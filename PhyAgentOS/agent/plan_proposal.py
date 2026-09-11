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
    validate_graph,
)


def compile_task_plan(
    task: AgentTaskRecord, nodes: list[dict[str, Any]], *, reason: str,
) -> PlanGraph:
    """Own protocol metadata, never select entities, Tools, or dependencies."""
    binding = task.primary_skill_binding
    if binding is None:
        raise ValueError("semantic plan submission requires a bound Skill")
    parsed = tuple(PlanNode.model_validate(node) for node in nodes)
    capabilities = {
        capability for tool in binding.required_tools if tool.planning_policy is not None
        for capability in tool.planning_policy.capabilities
    }
    if any(node.capability not in capabilities for node in parsed):
        raise ValueError("semantic plan references a capability outside the bound Skill")
    payload = {
        "task_id": task.task_id,
        "revision_id": f"revision_{uuid4().hex[:16]}",
        "nodes": [node.model_dump(mode="json") for node in parsed],
        "planner_decision_digest": canonical_sha256({"nodes": nodes, "reason": reason}),
        "policy_snapshot_digest": canonical_sha256({
            "skill_document_sha256": binding.skill_document_sha256,
            "tools": [tool.model_dump(mode="json") for tool in binding.required_tools],
        }),
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    validate_graph(graph)
    return graph
