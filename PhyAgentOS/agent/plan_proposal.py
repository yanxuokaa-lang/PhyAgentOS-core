"""Compile model-selected semantic nodes into the existing planning protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.forge.manipulation import (
    CapabilitySnapshot,
    CoordinationMode,
)
from PhyAgentOS.forge.task import AgentTaskRecord
from PhyAgentOS.planning import (
    PlanGraph,
    PlanNode,
    canonical_sha256,
    plan_graph_digest,
    required_node_binding_keys,
    validate_condition_keys,
    validate_graph,
)


def compile_task_plan(
    task: AgentTaskRecord,
    nodes: list[dict[str, Any]],
    *,
    reason: str,
    initial_evidence_refs: tuple[str, ...] | None = None,
    initial_condition_facts: dict[str, bool] | None = None,
) -> PlanGraph:
    """Own protocol metadata, never select entities, Tools, or dependencies."""
    binding = task.primary_skill_binding
    tools = binding.required_tools if binding is not None else tuple(task.tool_bindings)
    if binding is None and task.runtime_binding is None:
        raise ValueError("semantic plan submission requires a bound Runtime")
    parsed = tuple(PlanNode.model_validate(node) for node in nodes)
    parsed = _complete_persisted_runtime_bindings(task, parsed)
    for node in parsed:
        validate_condition_keys(node.conditions)
    capabilities = {
        capability for tool in tools if tool.planning_policy is not None
        for capability in tool.planning_policy.capabilities
    }
    preplan_capabilities = {
        capability
        for tool in tools
        if tool.planning_policy is not None
        and tool.semantics == "query"
        for capability in tool.planning_policy.capabilities
    }
    unsupported = sorted({
        node.capability for node in parsed if node.capability not in capabilities
    })
    if unsupported:
        available = ", ".join(sorted(capabilities)) or "<none>"
        raise ValueError(
            "semantic plan references capabilities outside the bound Skill: "
            f"{', '.join(unsupported)}; available capabilities: {available}"
        )
    unbindable: list[str] = []
    for node in parsed:
        candidates = tuple(
            tool.planning_policy
            for tool in tools
            if tool.planning_policy is not None
            and node.capability in tool.planning_policy.capabilities
        )
        if any(
            set(required_node_binding_keys(policy)).issubset(node.input_bindings)
            for policy in candidates
        ):
            continue
        candidate_details = ", ".join(
            f"{policy.tool_id} missing "
            f"[{', '.join(key for key in required_node_binding_keys(policy) if key not in node.input_bindings)}]"
            for policy in candidates
        ) or "<none>"
        unbindable.append(f"{node.node_id}: {candidate_details}")
    if unbindable:
        raise ValueError(
            "semantic plan contains node(s) that no frozen ToolPolicy can bind: "
            + "; ".join(unbindable)
            + "; materialize only the current scene-bound segment and continue after fresh observation/binding"
        )
    root_produced_evidence = {
        node.node_id: node.produced_evidence
        for node in parsed
        if (
            not node.dependencies
            and node.capability in preplan_capabilities
            and node.produced_evidence
        )
    }
    if root_produced_evidence:
        details = "; ".join(
            f"{node_id}: {', '.join(values)}"
            for node_id, values in sorted(root_produced_evidence.items())
        )
        raise ValueError(
            "root discovery nodes cannot declare produced_evidence before their Tool "
            f"has a terminal result: {details}; leave produced_evidence empty and "
            "use the exact paos_record.evidence_refs for later dependent nodes"
        )
    if initial_evidence_refs is not None:
        initial = set(initial_evidence_refs)
        unavailable_evidence = {
            node.node_id: tuple(
                reference for reference in node.required_evidence if reference not in initial
            )
            for node in parsed
            if any(reference not in initial for reference in node.required_evidence)
        }
        if unavailable_evidence:
            details = "; ".join(
                f"{node_id}: {', '.join(missing)}"
                for node_id, missing in sorted(unavailable_evidence.items())
            )
            raise ValueError(
                "semantic nodes require evidence not present in the current trusted "
                f"context: {details}; use exact persisted paos_record.evidence_refs "
                "for current evidence and dependencies for future Tool results"
            )
    if initial_condition_facts is not None:
        root_condition_errors = {
            node.node_id: tuple(
                condition for condition in node.conditions
                if initial_condition_facts.get(condition) is not True
            )
            for node in parsed
            if not node.dependencies
            and any(initial_condition_facts.get(condition) is not True for condition in node.conditions)
        }
        if root_condition_errors:
            details = "; ".join(
                f"{node_id}: {', '.join(missing)}"
                for node_id, missing in sorted(root_condition_errors.items())
            )
            raise ValueError(
                "root semantic nodes require condition facts that are not currently true: "
                f"{details}; move prose into obligation/input_bindings or create a predecessor "
                "Tool node that returns the trusted condition fact"
            )
    payload = {
        "task_id": task.task_id,
        "revision_id": f"revision_{uuid4().hex[:16]}",
        "nodes": [node.model_dump(mode="json") for node in parsed],
        "planner_decision_digest": canonical_sha256({"nodes": nodes, "reason": reason}),
        "policy_snapshot_digest": canonical_sha256({
            "skill_document_sha256": (
                binding.skill_document_sha256 if binding is not None else None
            ),
            "runtime_binding_id": (
                task.runtime_binding.binding_id if task.runtime_binding is not None else None
            ),
            "tools": [tool.model_dump(mode="json") for tool in tools],
        }),
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    validate_graph(graph)
    return graph


def _complete_persisted_runtime_bindings(
    task: AgentTaskRecord, nodes: tuple[PlanNode, ...]
) -> tuple[PlanNode, ...]:
    """Carry unambiguous producer references into consumer node bindings.

    Agent-composed plans intentionally choose semantic nodes, while the
    Coordinator owns exact persisted producer facts.  Preparation/acquisition
    consumers must not depend on the model copying a destination or capability
    URI into every later selection.  Only values already frozen in this graph
    or a unique current-revision capabilities result are propagated; ambiguous or
    stale values remain absent and are rejected by normal selection validation.
    """
    destination_by_entity: dict[str, set[str]] = {}
    for node in nodes:
        entity = node.input_bindings.get("entity_ref")
        destination = node.input_bindings.get("destination_ref")
        if isinstance(entity, str) and isinstance(destination, str):
            destination_by_entity.setdefault(entity, set()).add(destination)

    capability_refs: set[str] = set()
    capability_arm_ids: dict[str, tuple[str, ...]] = {}
    capability_topologies: dict[str, str] = {}
    goal_sources: dict[str, set[str]] = {}
    goal_entities_by_destination: dict[str, set[str]] = {}
    predecessor_destinations: dict[str, set[str]] = {}
    predecessor_entities: dict[str, set[str]] = {}
    observed_to_execution: dict[str, set[str]] = {}
    for revision in task.revisions:
        for record in revision.execution_records:
            facts = response_facts(record.response)
            if record.status == "succeeded" and record.tool_id == "task.goal":
                if facts.get("goal_source", facts.get("geometry_source")) == "benchmark_task_definition":
                    for goal in facts.get("goals", ()):
                        if not isinstance(goal, Mapping):
                            continue
                        entity = goal.get("execution_entity_ref")
                        destination = goal.get("destination_ref")
                        if isinstance(entity, str) and isinstance(destination, str):
                            goal_sources.setdefault(entity, set()).add(destination)
                            goal_entities_by_destination.setdefault(destination, set()).add(entity)

    # Scene-bound facts must come from the revision being compiled. Task goals
    # are task-specification facts and may outlive a scene; capabilities,
    # identity correspondence, targets, and candidates may not.
    active_revision = task.active_revision
    for record in active_revision.execution_records:
        facts = response_facts(record.response)
        if record.status != "succeeded":
            continue
        if record.tool_id == "scene.bind":
            for item in facts.get("entities", ()):
                if not isinstance(item, Mapping):
                    continue
                observed = item.get("entity_ref")
                execution = item.get("execution_entity_ref")
                if isinstance(observed, str) and isinstance(execution, str):
                    observed_to_execution.setdefault(observed, set()).add(execution)
        if record.tool_id in {"grasp.propose", "manipulation.target", "scene.bind"}:
            entities = set()
            entity = facts.get("entity_ref")
            if isinstance(entity, str):
                entities.add(entity)
            for candidate in facts.get("candidates", ()):
                if isinstance(candidate, Mapping) and isinstance(candidate.get("entity_ref"), str):
                    entities.add(candidate["entity_ref"])
            destination = facts.get("destination_ref")
            if isinstance(destination, str) and len(entities) == 1:
                predecessor_destinations.setdefault(next(iter(entities)), set()).add(destination)
            if entities:
                predecessor_entities[record.node_id or record.tool_id] = entities
        if record.tool_id != "manipulation.capabilities":
            continue
        snapshot_ref = facts.get("snapshot_ref") or facts.get("capability_snapshot_ref")
        if isinstance(snapshot_ref, str) and snapshot_ref.startswith("artifact://"):
            capability_refs.add(snapshot_ref)
            snapshot_payload = {
                key: facts[key]
                for key in CapabilitySnapshot.model_fields
                if key in facts
            }
            try:
                snapshot = CapabilitySnapshot.model_validate(snapshot_payload)
            except ValueError:
                continue
            capability_topologies[snapshot_ref] = snapshot.topology
            capability_arm_ids[snapshot_ref] = tuple(
                arm.arm_id
                for arm in snapshot.arms
                if arm.availability == "available"
            )

    # A preparation/acquisition node may carry the Runtime execution identity
    # while its grasp predecessor is the node that needs the observed identity.
    # Propagate only a unique scene.bind correspondence; never derive an ID from
    # color, category, or string spelling.
    execution_to_observed: dict[str, set[str]] = {}
    for observed, executions in observed_to_execution.items():
        for execution in executions:
            execution_to_observed.setdefault(execution, set()).add(observed)
    node_by_id = {node.node_id: node for node in nodes}
    grasp_execution_targets: dict[str, set[str]] = {}
    for node in nodes:
        execution = node.input_bindings.get("execution_entity_ref")
        destination = node.input_bindings.get("destination_ref")
        if not isinstance(execution, str) and isinstance(destination, str):
            destination_entities = goal_entities_by_destination.get(destination, set())
            if len(destination_entities) == 1:
                execution = next(iter(destination_entities))
        if not isinstance(execution, str):
            continue
        if node.capability == "grasp.propose":
            grasp_execution_targets.setdefault(node.node_id, set()).add(execution)
        for dependency in node.dependencies:
            predecessor = node_by_id.get(dependency)
            if predecessor is not None and predecessor.capability == "grasp.propose":
                grasp_execution_targets.setdefault(dependency, set()).add(execution)

    proposed_entities = {
        node.node_id: {entity}
        for node in nodes
        if isinstance((entity := node.input_bindings.get("entity_ref")), str)
    }

    completed: list[PlanNode] = []
    for node in nodes:
        bindings = dict(node.input_bindings)
        if node.capability == "grasp.propose":
            execution_targets = grasp_execution_targets.get(node.node_id, set())
            if len(execution_targets) == 1:
                observed_entities = execution_to_observed.get(next(iter(execution_targets)), set())
                if len(observed_entities) == 1:
                    expected_entity = next(iter(observed_entities))
                    # A semantic Agent label (for example
                    # ``entity://red-block-1``) is not an execution identity.
                    # When the current goal/destination uniquely identifies the
                    # object, Coordinator-owned scene.bind correspondence is
                    # authoritative and compiles the observed key here.
                    bindings["entity_ref"] = expected_entity
        if node.capability in {"manipulation.prepare", "object.acquire", "object.place"}:
            entity = bindings.get("entity_ref")
            execution_entity = bindings.get("execution_entity_ref")
            destination = bindings.get("destination_ref")
            if not isinstance(execution_entity, str) and isinstance(destination, str):
                destination_entities = goal_entities_by_destination.get(destination, set())
                if len(destination_entities) == 1:
                    execution_entity = next(iter(destination_entities))
            if not isinstance(entity, str) and isinstance(execution_entity, str):
                observed_entities = execution_to_observed.get(execution_entity, set())
                if len(observed_entities) == 1:
                    entity = next(iter(observed_entities))
                    bindings["entity_ref"] = entity
            elif isinstance(execution_entity, str):
                observed_entities = execution_to_observed.get(execution_entity, set())
                if len(observed_entities) == 1:
                    entity = next(iter(observed_entities))
                    bindings["entity_ref"] = entity
            if not isinstance(entity, str):
                predecessor_values = [
                    values for key, values in predecessor_entities.items()
                    if key in node.dependencies
                ]
                predecessor_values.extend(
                    values for key, values in proposed_entities.items()
                    if key in node.dependencies
                )
                merged = set().union(*predecessor_values) if predecessor_values else set()
                if len(merged) == 1:
                    entity = next(iter(merged))
                    bindings["entity_ref"] = entity
            destinations = set(destination_by_entity.get(entity, set()))
            if isinstance(execution_entity, str):
                destinations |= goal_sources.get(execution_entity, set())
            destinations |= goal_sources.get(entity, set())
            execution_entities = observed_to_execution.get(entity, set())
            if len(execution_entities) == 1:
                destinations |= goal_sources.get(next(iter(execution_entities)), set())
            destinations |= predecessor_destinations.get(entity, set())
            if node.capability in {"manipulation.prepare", "object.place"} and len(destinations) == 1:
                bindings.setdefault("destination_ref", next(iter(destinations)))
            if len(capability_refs) == 1:
                capability_ref = next(iter(capability_refs))
                bindings.setdefault("capability_snapshot_ref", capability_ref)
                if node.capability == "manipulation.prepare":
                    available_arms = capability_arm_ids.get(capability_ref, ())
                    topology = capability_topologies.get(capability_ref)
                    if "coordination_mode" not in bindings and topology is not None:
                        bindings["coordination_mode"] = {
                            "single_arm": CoordinationMode.SINGLE_ARM.value,
                            "dual_independent": CoordinationMode.ALTERNATIVE_ARM.value,
                            "dual_coordinated": CoordinationMode.BIMANUAL.value,
                        }[topology]
                    selected_arms = bindings.get("allowed_arms")
                    if selected_arms is not None:
                        if not isinstance(selected_arms, (list, tuple)):
                            raise ValueError(
                                f"{node.node_id}: allowed_arms must be copied as an arm_id list"
                            )
                        invalid = [arm for arm in selected_arms if arm not in available_arms]
                        if invalid:
                            raise ValueError(
                                f"{node.node_id}: allowed_arms contains identities absent from "
                                f"the capability snapshot: {', '.join(map(str, invalid))}; "
                                f"available arm_id values: {', '.join(available_arms)}"
                            )
                    elif available_arms and bindings.get("coordination_mode") in {
                        CoordinationMode.SINGLE_ARM.value,
                        CoordinationMode.ALTERNATIVE_ARM.value,
                        CoordinationMode.BIMANUAL.value,
                    }:
                        bindings["allowed_arms"] = list(available_arms)
        completed.append(node.model_copy(update={"input_bindings": bindings}))
    return tuple(completed)
