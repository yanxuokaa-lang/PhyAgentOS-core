"""Compile model-selected semantic nodes into the existing planning protocol."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PhyAgentOS.forge.task import AgentTaskRecord
from PhyAgentOS.planning import (
    PlanGraph,
    PlanNode,
    canonical_sha256,
    plan_graph_digest,
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
            set(policy.input_binding_keys).issubset(node.input_bindings)
            for policy in candidates
        ):
            continue
        candidate_details = ", ".join(
            f"{policy.tool_id} missing "
            f"[{', '.join(key for key in policy.input_binding_keys if key not in node.input_bindings)}]"
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
