"""AgentLoop bridge for PAOS agent-composed planning.

The bridge is deliberately a read-only adapter.  It exposes the current
PlanGraph ready set and performs pure admission before a Forge Tool wrapper is
invoked.  Task lifecycle, Gateway transport, evidence persistence, and motion
authority remain owned by their existing components.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Callable

from PhyAgentOS.forge.manipulation import ManipulationIntent
from PhyAgentOS.planning import (
    AdmissionContext,
    AdmissionDecision,
    PlanGraph,
    PlanningExecutionBinding,
    ToolCallEnvelope,
    ToolSpecPolicy,
    admit_tool_call,
    canonical_sha256,
    derive_ready_nodes,
    explain_node_readiness,
    plan_node_digest,
    required_argument_keys,
    required_node_binding_keys,
    tool_input_binding_digest,
    validate_tool_arguments,
)


class PlanningDispatchError(ValueError):
    """A Forge Tool call cannot be admitted by the active semantic graph."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "planning_selection_rejected",
        failure_owner: str = "agent_arguments",
        retryable_in_revision: bool = True,
        requires_replan: bool = False,
        missing_fields: tuple[str, ...] = (),
        recommended_action: str = "correct_arguments_and_retry_selection",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.failure_owner = failure_owner
        self.retryable_in_revision = retryable_in_revision
        self.requires_replan = requires_replan
        self.missing_fields = tuple(sorted(set(missing_fields)))
        self.recommended_action = recommended_action

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": "planning_selection",
            "code": self.code,
            "failure_owner": self.failure_owner,
            "message": str(self),
            "missing_fields": list(self.missing_fields),
            "retryable_in_revision": self.retryable_in_revision,
            "requires_replan": self.requires_replan,
            "recommended_action": self.recommended_action,
        }


class AgentComposedDispatch:
    """Pure admission facade used by AgentLoop for one frozen PlanGraph."""

    _FORGE_CREATE_TOOLS = {
        "forge_tool_query": "query",
        "forge_tool_start_action": "action",
        "forge_tool_start_session": "session",
    }

    def __init__(
        self,
        graph: PlanGraph,
        policies: tuple[ToolSpecPolicy, ...],
        context: AdmissionContext,
        context_provider: Callable[[str], AdmissionContext] | None = None,
        input_schemas: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        if len({policy.tool_id for policy in policies}) != len(policies):
            raise PlanningDispatchError("planning ToolSpec identities must be unique")
        self.graph = graph
        self.policies = policies
        self.context = context
        self.context_provider = context_provider
        self._policies = {policy.tool_id: policy for policy in policies}
        self._input_schemas = {
            tool_id: deepcopy(dict(schema))
            for tool_id, schema in (input_schemas or {}).items()
        }

    @classmethod
    def from_task(
        cls,
        task: Any,
        *,
        context_provider: Callable[[str], AdmissionContext],
    ) -> "AgentComposedDispatch":
        """Build a dispatch from an existing task aggregate and frozen binding."""
        graph = getattr(getattr(task, "active_revision", None), "plan_graph", None)
        if graph is None:
            raise PlanningDispatchError("AgentTask active revision has no concrete PlanGraph")
        binding = getattr(task, "primary_skill_binding", None)
        enrolled = (
            getattr(binding, "required_tools", ())
            if binding is not None
            else getattr(task, "tool_bindings", ())
        )
        if binding is None and getattr(task, "runtime_binding", None) is None:
            raise PlanningDispatchError("AgentTask has no frozen Runtime binding")
        policies = tuple(
            item.planning_policy
            for item in enrolled
            if item.planning_policy is not None
        )
        input_schemas = {
            item.tool_id: item.input_schema
            for item in enrolled
            if item.planning_policy is not None and item.input_schema is not None
        }
        if not policies:
            raise PlanningDispatchError(
                "Runtime-bound task has no enrolled planning ToolSpec projections"
            )
        context = context_provider(graph.task_id)
        if not isinstance(context, AdmissionContext):
            raise PlanningDispatchError("planning context provider returned an invalid context")
        return cls(
            graph,
            policies,
            context,
            context_provider=context_provider,
            input_schemas=input_schemas,
        )

    def describe(self) -> dict[str, Any]:
        """Return bounded data for the Agent; no provider payloads are exposed."""
        context = self._current_context()
        settlements = dict(context.settlements)
        conditions = dict(context.condition_facts)
        ready = derive_ready_nodes(
            self.graph,
            settlements,
            set(context.evidence_refs),
            conditions,
        )
        nodes = {node.node_id: node for node in self.graph.nodes}
        if conditions.get("scene_current") is False:
            ready = tuple(
                node.node_id
                for node in self.graph.nodes
                if node.node_id not in settlements
                and all(settlements.get(dep) == "completed" for dep in node.dependencies)
                and any(
                    node.capability in policy.capabilities and policy.refreshes_scene
                    for policy in self.policies
                )
            )
        diagnostics = []
        for node in self.graph.nodes:
            if node.node_id in settlements:
                continue
            item = explain_node_readiness(
                node,
                settlements,
                set(context.evidence_refs),
                conditions,
            )
            candidate_policies = tuple(
                policy
                for policy in self.policies
                if node.capability in policy.capabilities
                and (conditions.get("scene_current") is not False or policy.refreshes_scene)
            )
            candidates = tuple(policy.tool_id for policy in candidate_policies)
            missing_node_bindings = {
                policy.tool_id: tuple(
                    key for key in required_node_binding_keys(policy)
                    if key not in node.input_bindings
                )
                for policy in candidate_policies
                if any(
                    key not in node.input_bindings
                    for key in required_node_binding_keys(policy)
                )
            }
            bindable = tuple(
                policy.tool_id
                for policy in candidate_policies
                if policy.tool_id not in missing_node_bindings
            )
            runtime_requirements = {
                policy.tool_id: self._required_runtime_arguments(policy)
                for policy in candidate_policies
                if self._required_runtime_arguments(policy)
            }
            required_arguments = {
                policy.tool_id: required_argument_keys(self._input_schemas.get(policy.tool_id))
                for policy in candidate_policies
                if required_argument_keys(self._input_schemas.get(policy.tool_id))
            }
            dependency_ready = node.node_id in ready
            item.update({
                "dependency_ready": dependency_ready,
                "selection_ready": dependency_ready and bool(bindable),
                "candidate_tool_ids": candidates,
                "bindable_tool_ids": bindable,
                "missing_node_bindings": missing_node_bindings,
                "missing_runtime_arguments": runtime_requirements,
                "required_tool_arguments": required_arguments,
            })
            if not candidates:
                item["blockers"] = tuple((*item["blockers"], "no_tool_candidate"))
            elif not bindable:
                item["blockers"] = tuple((*item["blockers"], "missing_node_bindings"))
            diagnostics.append(item)
        return {
            "ok": True,
            "mode": "agent_composed",
            "task_id": self.graph.task_id,
            "revision_id": self.graph.revision_id,
            "graph_digest": self.graph.graph_digest,
            "scene_revision": context.scene_revision,
            "context_digest": canonical_sha256(context.model_dump(mode="json")),
            "ready_nodes": [
                {
                    "node_id": node_id,
                    "obligation_id": nodes[node_id].obligation_id,
                    "capability": nodes[node_id].capability,
                    "candidate_tool_ids": [
                        policy.tool_id
                        for policy in self.policies
                        if nodes[node_id].capability in policy.capabilities
                        and (conditions.get("scene_current") is not False or policy.refreshes_scene)
                        and set(required_node_binding_keys(policy)).issubset(nodes[node_id].input_bindings)
                    ],
                    **(
                        {"missing_runtime_arguments": {
                            policy.tool_id: self._required_runtime_arguments(policy)
                            for policy in self.policies
                            if nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and self._required_runtime_arguments(policy)
                        }}
                        if any(
                            nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and self._required_runtime_arguments(policy)
                            for policy in self.policies
                        )
                        else {}
                    ),
                    **(
                        {"required_tool_arguments": {
                            policy.tool_id: required_argument_keys(
                                self._input_schemas.get(policy.tool_id)
                            )
                            for policy in self.policies
                            if nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and required_argument_keys(
                                self._input_schemas.get(policy.tool_id)
                            )
                        }}
                        if any(
                            nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and required_argument_keys(
                                self._input_schemas.get(policy.tool_id)
                            )
                            for policy in self.policies
                        )
                        else {}
                    ),
                    **(
                        {"frozen_tool_input_schemas": {
                            policy.tool_id: deepcopy(self._input_schemas[policy.tool_id])
                            for policy in self.policies
                            if nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and policy.tool_id in self._input_schemas
                        }}
                        if any(
                            nodes[node_id].capability in policy.capabilities
                            and (
                                conditions.get("scene_current") is not False
                                or policy.refreshes_scene
                            )
                            and set(required_node_binding_keys(policy)).issubset(
                                nodes[node_id].input_bindings
                            )
                            and policy.tool_id in self._input_schemas
                            for policy in self.policies
                        )
                        else {}
                    ),
                }
                for node_id in ready
                if any(
                    nodes[node_id].capability in policy.capabilities
                    and (conditions.get("scene_current") is not False or policy.refreshes_scene)
                    and set(required_node_binding_keys(policy)).issubset(nodes[node_id].input_bindings)
                    for policy in self.policies
                )
            ],
            "node_diagnostics": diagnostics,
            "motion_authorized": False,
        }

    @property
    def current_scene_revision(self) -> str:
        """Return the trusted scene identity used by current admission."""
        return self._current_context().scene_revision

    def admit_forge_tool(
        self, wrapper_name: str, arguments: Mapping[str, Any]
    ) -> AdmissionDecision | None:
        """Admit a task-bound Forge create call, or return ``None`` for diagnostics.

        Status/result/cancel wrappers are control-plane reconciliation calls and
        remain governed by Coordinator ownership checks; only calls that create
        a Query/Action/Session are subject to semantic-node admission here.
        """
        semantics = self._FORGE_CREATE_TOOLS.get(wrapper_name)
        if semantics is None:
            return None
        task_id = arguments.get("task_id")
        if task_id is None:
            return None
        if not isinstance(task_id, str) or task_id != self.graph.task_id:
            return AdmissionDecision(
                allowed=False,
                code="identity_mismatch",
                detail="task-bound Forge call is not bound to the active PlanGraph",
                node_id="unknown",
                tool_id=str(arguments.get("tool_id", "unknown")),
            )
        tool_id = arguments.get("tool_id")
        binding = arguments.get("planning_binding")
        if not isinstance(tool_id, str) or not isinstance(binding, Mapping):
            return AdmissionDecision(
                allowed=False,
                code="missing_planning_binding",
                detail="agent-composed Forge calls require a complete planning_binding",
                node_id="unknown",
                tool_id=str(tool_id or "unknown"),
            )
        policy = self._policies.get(tool_id)
        if policy is None or policy.semantics != semantics:
            return AdmissionDecision(
                allowed=False,
                code="tool_not_declared",
                detail="Tool has no matching frozen planning projection",
                node_id=str(binding.get("node_id", "unknown")),
                tool_id=tool_id,
            )
        try:
            planning_binding = PlanningExecutionBinding.model_validate(dict(binding))
            node_id = planning_binding.node_id
            input_digest = planning_binding.input_binding_digest
            node = next(node for node in self.graph.nodes if node.node_id == node_id)
            if planning_binding.node_digest != plan_node_digest(node):
                raise PlanningDispatchError("planning binding node digest does not match the active graph")
            if planning_binding.obligation_id != node.obligation_id:
                raise PlanningDispatchError("planning binding obligation does not match the active graph")
            idempotency = hashlib.sha256(
                json.dumps(
                    {
                        "task_id": task_id,
                        "revision_id": self.graph.revision_id,
                        "node_id": node_id,
                        "tool_id": tool_id,
                        "arguments": arguments.get("arguments", {}),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            context = self._current_context()
            call = ToolCallEnvelope(
                task_id=task_id,
                revision_id=self.graph.revision_id,
                node_id=node_id,
                tool_id=tool_id,
                tool_spec_digest=policy.spec_digest,
                input_binding_digest=input_digest,
                arguments=dict(arguments.get("arguments", {})),
                caller_id="paos:agent-loop",
                scene_revision=context.scene_revision,
                idempotency_key=idempotency,
                semantics=semantics,
            )
        except (KeyError, StopIteration, TypeError, ValueError) as exc:
            return AdmissionDecision(
                allowed=False,
                code="invalid_planning_binding",
                detail=f"planning binding is invalid: {exc}",
                node_id=str(binding.get("node_id", "unknown")),
                tool_id=tool_id,
            )
        return admit_tool_call(self.graph, call, policy, context)

    def prepare_selection(
        self,
        *,
        node_id: str,
        tool_id: str,
        arguments: Mapping[str, Any],
        decision_reason: str,
    ) -> dict[str, Any]:
        """Validate a ready-node Tool choice without invoking a Gateway."""
        context = self._current_context()
        node = next((item for item in self.graph.nodes if item.node_id == node_id), None)
        policy = self._policies.get(tool_id)
        if node is None:
            raise PlanningDispatchError(
                "selected planning node is not in the active graph",
                code="stale_planning_node",
                failure_owner="agent_state",
                retryable_in_revision=False,
                recommended_action="refresh_active_plan",
            )
        if policy is None or node.capability not in policy.capabilities:
            raise PlanningDispatchError(
                "selected Tool is not declared for the planning node",
                code="tool_not_declared_for_node",
                missing_fields=("tool_id",),
                recommended_action="choose_candidate_tool",
            )
        # These references are frozen node inputs when the planning compiler
        # can resolve one persisted producer.  Reuse them here so the Agent
        # selects candidate payloads without manually duplicating opaque
        # destination/capability URIs in every prepare/acquire receipt.
        arguments = dict(arguments)
        for key in ("destination_ref", "capability_snapshot_ref"):
            if key not in arguments and key in node.input_bindings:
                arguments[key] = node.input_bindings[key]
        missing_node_bindings = tuple(
            key for key in required_node_binding_keys(policy)
            if key not in node.input_bindings
        )
        if missing_node_bindings:
            raise PlanningDispatchError(
                "selected Tool cannot bind the semantic node; missing frozen node bindings: "
                + ", ".join(missing_node_bindings),
                code="node_tool_binding_incompatible",
                failure_owner="plan_contract",
                retryable_in_revision=False,
                requires_replan=True,
                missing_fields=missing_node_bindings,
                recommended_action="replace_plan_segment",
            )
        conditions = dict(context.condition_facts)
        ready = derive_ready_nodes(
            self.graph,
            dict(context.settlements),
            set(context.evidence_refs),
            conditions,
        )
        if conditions.get("scene_current") is False:
            settlements = dict(context.settlements)
            ready = tuple(
                item.node_id
                for item in self.graph.nodes
                if item.node_id not in settlements
                and all(settlements.get(dep) == "completed" for dep in item.dependencies)
                and any(
                    item.capability in candidate.capabilities and candidate.refreshes_scene
                    for candidate in self.policies
                )
            )
        if node_id not in ready:
            raise PlanningDispatchError(
                "selected planning node is not dependency-ready",
                code="node_not_ready",
                failure_owner="agent_state",
                retryable_in_revision=True,
                recommended_action="execute_ready_predecessor_or_refresh_ready_projection",
            )
        if conditions.get("scene_current") is False and not policy.refreshes_scene:
            raise PlanningDispatchError(
                "a fresh scene observation is required before this Tool",
                code="fresh_observation_required",
                failure_owner="runtime_context",
                retryable_in_revision=True,
                recommended_action="execute_scene_refresh_node",
            )
        if not isinstance(decision_reason, str) or not decision_reason.strip():
            raise PlanningDispatchError(
                "decision_reason must be non-empty",
                code="missing_selection_arguments",
                missing_fields=("decision_reason",),
            )
        final_arguments = self._build_trusted_arguments(
            policy=policy,
            node=node,
            arguments=arguments,
        )
        input_schema = self._input_schemas.get(tool_id)
        if input_schema is not None:
            issues = validate_tool_arguments(input_schema, final_arguments)
            if issues:
                missing = tuple(
                    key
                    for key in required_argument_keys(input_schema)
                    if key not in final_arguments
                )
                raise PlanningDispatchError(
                    "selected Tool arguments violate the frozen input schema: "
                    + "; ".join(issues),
                    code="tool_input_schema_invalid",
                    failure_owner="agent_arguments",
                    missing_fields=missing,
                    recommended_action="select_values_from_bounded_node_context",
                )
        for key in policy.input_binding_keys:
            if key not in node.input_bindings or final_arguments.get(key) != node.input_bindings[key]:
                raise PlanningDispatchError(
                    f"Tool argument {key!r} does not match the node",
                    code="semantic_binding_mismatch",
                    missing_fields=(key,),
                )
        return {
            "task_id": self.graph.task_id,
            "revision_id": self.graph.revision_id,
            "node_id": node_id,
            "node_digest": plan_node_digest(node),
            "obligation_id": node.obligation_id,
            "tool_id": tool_id,
            "semantics": policy.semantics,
            "candidate_tool_ids": tuple(
                item.tool_id for item in self.policies
                if node.capability in item.capabilities and item.semantics == policy.semantics
            ),
            "input_binding_digest": tool_input_binding_digest(final_arguments),
            "tool_arguments": final_arguments,
            "scene_revision": context.scene_revision,
            "context_digest": canonical_sha256(context.model_dump(mode="json")),
            "evidence_refs": tuple(context.evidence_refs),
            "decision_reason": decision_reason.strip(),
        }

    def _build_trusted_arguments(
        self,
        *,
        policy: ToolSpecPolicy,
        node: Any,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        final_arguments = dict(arguments)
        if policy.trusted_argument_builder is None:
            return final_arguments
        if policy.trusted_argument_builder != "manipulation_intent_v2":
            raise PlanningDispatchError(
                "ToolSpec trusted argument builder is unsupported",
                code="unsupported_trusted_argument_builder",
                failure_owner="plan_contract",
                retryable_in_revision=False,
                requires_replan=True,
                recommended_action="repair_tool_policy",
            )

        supplied = final_arguments.pop("intent", None)
        semantic_keys = {
            "goal",
            "success_criteria",
            "allowed_arms",
            "coordination_mode",
            "constraints",
        }
        flat_supplied = {
            key: final_arguments.pop(key)
            for key in semantic_keys
            if key in final_arguments
        }
        node_intent = node.input_bindings.get("intent")
        flat_node = {
            key: node.input_bindings[key]
            for key in semantic_keys
            if key in node.input_bindings
        }
        if supplied is not None and not isinstance(supplied, Mapping):
            raise PlanningDispatchError(
                "nested Tool intent semantics must be an object",
                code="invalid_selection_arguments",
                missing_fields=("intent",),
            )
        if node_intent is not None and not isinstance(node_intent, Mapping):
            raise PlanningDispatchError(
                "nested node intent semantics must be an object",
                code="invalid_node_semantics",
                failure_owner="plan_contract",
                retryable_in_revision=False,
                requires_replan=True,
                missing_fields=("intent",),
                recommended_action="replace_plan_segment",
            )
        if supplied is not None and flat_supplied and dict(supplied) != flat_supplied:
            raise PlanningDispatchError(
                "nested and flat Tool intent semantics conflict",
                code="semantic_intent_mismatch",
            )
        if node_intent is not None and flat_node and dict(node_intent) != flat_node:
            raise PlanningDispatchError(
                "nested and flat node intent semantics conflict",
                code="invalid_node_semantics",
                failure_owner="plan_contract",
                retryable_in_revision=False,
                requires_replan=True,
                recommended_action="replace_plan_segment",
            )
        supplied_semantic = supplied if supplied is not None else (flat_supplied or None)
        node_semantic = node_intent if node_intent is not None else (flat_node or None)
        if supplied_semantic is not None and node_semantic is not None and dict(supplied_semantic) != dict(node_semantic):
            raise PlanningDispatchError(
                "Tool intent does not match the semantic node",
                code="semantic_intent_mismatch",
            )
        semantic = supplied_semantic if supplied_semantic is not None else node_semantic
        if not isinstance(semantic, Mapping):
            raise PlanningDispatchError(
                "manipulation intent semantics are required in Tool arguments or node input_bindings",
                code="missing_runtime_arguments",
                missing_fields=("goal", "success_criteria", "allowed_arms", "coordination_mode"),
            )
        owned_keys = {
            "version",
            "task_id",
            "revision_id",
            "node_id",
            "node_digest",
            "entity_ref",
            "observation_ref",
            "scene_revision",
            "observation_frame_id",
            "calibration_ref",
            "candidate_set_ref",
            "motion_authorized",
        }
        unexpected = set(semantic) - semantic_keys
        if unexpected:
            label = "Coordinator-owned" if unexpected & owned_keys else "unsupported"
            raise PlanningDispatchError(
                f"manipulation intent contains {label} fields: {', '.join(sorted(unexpected))}",
                code="invalid_selection_arguments",
            )
        missing_runtime = tuple(
            key
            for key in self._required_runtime_arguments(policy)
            if key not in final_arguments or final_arguments[key] is None
        )
        if missing_runtime:
            raise PlanningDispatchError(
                "manipulation preparation omitted required Runtime arguments: "
                + ", ".join(missing_runtime),
                code="missing_runtime_arguments",
                missing_fields=missing_runtime,
            )
        candidates = final_arguments.get("candidates")
        entity_refs = {
            item.get("entity_ref")
            for item in candidates
            if isinstance(item, Mapping) and isinstance(item.get("entity_ref"), str)
        } if isinstance(candidates, list) else set()
        entity_ref = node.input_bindings.get("entity_ref")
        if not isinstance(entity_ref, str) and len(entity_refs) == 1:
            entity_ref = next(iter(entity_refs))
        if not isinstance(entity_ref, str) or entity_refs != {entity_ref}:
            raise PlanningDispatchError(
                "manipulation candidates must bind exactly one semantic node entity",
                code="candidate_entity_mismatch",
                missing_fields=("candidates", "entity_ref"),
            )
        for required in ("destination_ref", "capability_snapshot_ref"):
            if not isinstance(final_arguments.get(required), str):
                raise PlanningDispatchError(
                    f"manipulation preparation requires {required}",
                    code="missing_runtime_arguments",
                    missing_fields=(required,),
                )

        intent_payload = {
            **dict(semantic),
            "version": "manipulation_intent_v2",
            "task_id": self.graph.task_id,
            "revision_id": self.graph.revision_id,
            "node_id": node.node_id,
            "node_digest": plan_node_digest(node),
            "entity_ref": entity_ref,
            "observation_ref": final_arguments.get("observation_ref"),
            "scene_revision": final_arguments.get("scene_revision"),
            "observation_frame_id": final_arguments.get("frame_id"),
            "calibration_ref": final_arguments.get("calibration_ref"),
            "candidate_set_ref": final_arguments.get("candidate_set_ref"),
            "motion_authorized": False,
        }
        try:
            intent = ManipulationIntent.model_validate(intent_payload)
        except ValueError as exc:
            raise PlanningDispatchError(
                f"manipulation intent is incomplete: {exc}",
                code="invalid_selection_arguments",
            ) from exc
        final_arguments["intent"] = intent.model_dump(mode="json")
        return final_arguments

    @staticmethod
    def _required_runtime_arguments(policy: ToolSpecPolicy) -> tuple[str, ...]:
        if policy.trusted_argument_builder != "manipulation_intent_v2":
            return ()
        return (
            "observation_ref",
            "scene_revision",
            "frame_id",
            "calibration_ref",
            "freshness_ms",
            "max_age_ms",
            "candidate_set_ref",
            "candidates",
            "destination_ref",
            "capability_snapshot_ref",
        )

    def _current_context(self) -> AdmissionContext:
        if self.context_provider is None:
            return self.context
        context = self.context_provider(self.graph.task_id)
        if not isinstance(context, AdmissionContext):
            raise PlanningDispatchError("planning context provider returned an invalid context")
        self.context = context
        return context


__all__ = ["AgentComposedDispatch", "PlanningDispatchError"]
