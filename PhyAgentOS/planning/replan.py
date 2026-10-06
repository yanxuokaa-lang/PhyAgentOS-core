"""Pure construction of bounded replan instructions."""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import NodeSettlement, PlanGraph, ReplanDelta, plan_node_digest


def build_replan_delta(
    graph: PlanGraph,
    settlement: NodeSettlement,
    *,
    retry: bool = True,
    fresh_evidence_requirements: Iterable[str] = (),
) -> ReplanDelta:
    if settlement.node_id not in {node.node_id for node in graph.nodes}:
        raise ValueError("settlement node is not in the graph")
    if settlement.status == "completed":
        raise ValueError("completed node does not require replanning")
    descendants = {settlement.node_id}
    changed = True
    while changed:
        changed = False
        for node in graph.nodes:
            if node.node_id not in descendants and set(node.dependencies) & descendants:
                descendants.add(node.node_id)
                changed = True
    invalidate = tuple(sorted(descendants - {settlement.node_id}))
    preserve = tuple(sorted(node.node_id for node in graph.nodes if node.node_id not in descendants))
    return ReplanDelta(
        task_id=graph.task_id,
        revision_id=graph.revision_id,
        preserve_node_ids=preserve,
        cancel_node_ids=(),
        invalidate_node_ids=invalidate,
        retry_parent_node_id=settlement.node_id if retry else None,
        fresh_evidence_requirements=tuple(dict.fromkeys(fresh_evidence_requirements)),
        reason=f"node {settlement.node_id} settled as {settlement.status}",
    )


def reconcile_replan_delta(
    graph: PlanGraph,
    delta: ReplanDelta,
    replacement: PlanGraph,
) -> ReplanDelta:
    """Bind preserve declarations to the Agent-selected replacement graph.

    ``build_replan_delta`` can only produce preserve *candidates* because the
    replacement graph does not exist yet. A recovery-only graph may therefore
    omit completed historical nodes without making their settlements part of
    the new revision. Nodes that are included must remain semantically
    unchanged; otherwise the proposal is rejected instead of carrying a
    settlement across changed obligations.
    """
    if delta.task_id != graph.task_id or delta.revision_id != graph.revision_id:
        raise ValueError("replan delta is not bound to the source graph")
    if replacement.task_id != graph.task_id or replacement.revision_id == graph.revision_id:
        raise ValueError("replacement graph is not a new graph for the source task")

    source_nodes = {node.node_id: node for node in graph.nodes}
    replacement_nodes = {node.node_id: node for node in replacement.nodes}
    effective: list[str] = []
    seen: set[str] = set()
    for node_id in delta.preserve_node_ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        source = source_nodes.get(node_id)
        if source is None:
            raise ValueError(f"preserve node {node_id!r} is absent from source graph")
        candidate = replacement_nodes.get(node_id)
        if candidate is None:
            continue
        if plan_node_digest(source) != plan_node_digest(candidate):
            raise ValueError(f"cannot preserve node {node_id!r}: replacement content changed")
        effective.append(node_id)

    return delta.model_copy(update={"preserve_node_ids": tuple(effective)})


__all__ = ["build_replan_delta", "reconcile_replan_delta"]
