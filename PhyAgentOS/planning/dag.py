"""Pure DAG validation and readiness calculations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import PlanGraph


def validate_graph(graph: PlanGraph) -> tuple[str, ...]:
    """Return a deterministic topological order or raise ``ValueError``."""
    ids = {node.node_id for node in graph.nodes}
    indegree = {node.node_id: len(node.dependencies) for node in graph.nodes}
    children = {node_id: [] for node_id in ids}
    for node in graph.nodes:
        for dependency in node.dependencies:
            if dependency not in ids:
                raise ValueError(f"unknown dependency: {dependency}")
            children[dependency].append(node.node_id)
    ready = sorted(node_id for node_id, count in indegree.items() if count == 0)
    order: list[str] = []
    while ready:
        node_id = ready.pop(0)
        order.append(node_id)
        for child in sorted(children[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(ids):
        raise ValueError("plan graph contains a dependency cycle")
    return tuple(order)


def evaluate_conditions(conditions: tuple[str, ...], facts: Mapping[str, bool]) -> bool:
    """Evaluate the intentionally small condition language: every named fact is true."""
    unknown = [condition for condition in conditions if condition not in facts]
    if unknown:
        return False
    return all(facts[condition] is True for condition in conditions)


def explain_node_readiness(
    node: Any,
    settlements: Mapping[str, str],
    evidence: set[str] | frozenset[str] = frozenset(),
    facts: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Explain why one semantic node is or is not ready.

    This is a pure diagnostic projection.  It does not turn effects into
    facts, infer evidence aliases, or relax any admission rule.  The caller
    may add Tool candidates, but the lower-level blockers come only from the
    trusted settlement/evidence/fact projections supplied here.
    """
    facts = facts or {}
    missing_dependencies = tuple(
        dependency
        for dependency in node.dependencies
        if settlements.get(dependency) != "completed"
    )
    missing_evidence = tuple(
        reference
        for reference in node.required_evidence
        if reference not in evidence
    )
    unknown_conditions = tuple(
        condition
        for condition in node.conditions
        if condition not in facts
    )
    false_conditions = tuple(
        condition
        for condition in node.conditions
        if facts.get(condition) is False
    )
    dependency_status = {
        dependency: settlements.get(dependency)
        for dependency in missing_dependencies
    }
    blockers: list[str] = []
    if missing_dependencies:
        blockers.append("dependencies")
    if missing_evidence:
        blockers.append("evidence")
    if unknown_conditions:
        blockers.append("unknown_conditions")
    if false_conditions:
        blockers.append("false_conditions")
    return {
        "node_id": node.node_id,
        "ready": not blockers,
        "blockers": tuple(blockers),
        "missing_dependencies": missing_dependencies,
        "dependency_status": dependency_status,
        "missing_evidence": missing_evidence,
        "unknown_conditions": unknown_conditions,
        "false_conditions": false_conditions,
    }


def derive_ready_nodes(
    graph: PlanGraph,
    settlements: Mapping[str, str],
    evidence: set[str] | frozenset[str] = frozenset(),
    facts: Mapping[str, bool] | None = None,
) -> tuple[str, ...]:
    """Return nodes whose dependencies, evidence, and conditions are satisfied."""
    validate_graph(graph)
    facts = facts or {}
    ready: list[str] = []
    for node in graph.nodes:
        if settlements.get(node.node_id) is not None:
            continue
        diagnostic = explain_node_readiness(node, settlements, evidence, facts)
        if not diagnostic["ready"]:
            continue
        ready.append(node.node_id)
    return tuple(sorted(ready))


def invalidate_stale_nodes(graph: PlanGraph, scene_revision: str, node_revisions: Mapping[str, str]) -> tuple[str, ...]:
    """Identify nodes whose previously captured scene revision is stale."""
    validate_graph(graph)
    known = {node.node_id for node in graph.nodes}
    unknown = set(node_revisions) - known
    if unknown:
        raise ValueError(f"node revision references unknown nodes: {sorted(unknown)}")
    return tuple(
        sorted(node.node_id for node in graph.nodes if node_revisions.get(node.node_id) != scene_revision)
    )
