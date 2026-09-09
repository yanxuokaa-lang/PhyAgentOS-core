"""Normalize execution outcomes without confusing unknown with failure."""

from __future__ import annotations

from .contracts import NodeSettlement, PlanNode, ToolResultEnvelope


def settle_node(node: PlanNode, result: ToolResultEnvelope, *, current_scene_revision: str) -> NodeSettlement:
    if result.node_id != node.node_id:
        raise ValueError("Tool result node does not match the settled node")
    facts = dict(
        task_id=result.task_id, revision_id=result.revision_id, node_id=node.node_id,
        evidence_refs=result.evidence_refs,
        scene_revision=result.new_scene_revision or current_scene_revision,
        source_tool_id=result.tool_id,
        world_change_started=True if result.world_changed else result.world_change_started,
        outcome_known=result.outcome_known,
    )
    if result.outcome_known is False:
        return NodeSettlement(**facts, status="outcome_unknown", failure_code=result.failure_code or "outcome_unknown")
    if result.status == "succeeded":
        if result.world_changed and result.new_scene_revision == current_scene_revision:
            return NodeSettlement(**facts, status="stale", failure_code="scene_revision_not_advanced")
        missing = set(node.produced_evidence) - set(result.evidence_refs)
        if missing:
            return NodeSettlement(**facts, status="failed", failure_code="missing_produced_evidence")
        return NodeSettlement(**facts, status="completed")
    if result.status in {"unknown"}:
        status = "outcome_unknown"
    elif result.status == "cancelled":
        status = "cancelled_before_start" if result.world_change_started is False else "outcome_unknown" if result.outcome_known is not True else "failed"
    else:
        status = "failed"
    return NodeSettlement(**facts, status=status, failure_code=result.failure_code or result.status)


__all__ = ["settle_node"]
