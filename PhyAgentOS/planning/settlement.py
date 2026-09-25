"""Normalize execution outcomes without confusing unknown with failure."""

from __future__ import annotations

from .contracts import NodeSettlement, PlanNode, ToolResultEnvelope


_COORDINATOR_EVIDENCE_PREFIXES = (
    "artifact://",
    "invocation:",
    "session:",
    "tool:",
)


def _is_coordinator_evidence_ref(value: str) -> bool:
    """Recognize references emitted by Coordinator or a persisted Runtime record."""
    return value.startswith(_COORDINATOR_EVIDENCE_PREFIXES)


def _missing_produced_evidence(node: PlanNode, result: ToolResultEnvelope) -> set[str]:
    """Validate opaque postconditions without treating semantic labels as facts.

    ``PlanNode.produced_evidence`` predates the opaque Runtime evidence refs and
    is still used for semantic postcondition labels.  A terminal Tool result may
    therefore satisfy those labels by producing a Coordinator-owned evidence
    ref, while an explicitly opaque declaration must still match exactly.
    """
    actual = set(result.evidence_refs)
    missing = set(node.produced_evidence) - actual
    if not missing:
        return set()
    missing_opaque = {
        value for value in missing if _is_coordinator_evidence_ref(value)
    }
    has_real_result_evidence = any(
        _is_coordinator_evidence_ref(value) for value in actual
    )
    if not missing_opaque and has_real_result_evidence:
        return set()
    return missing


def settle_node(
    node: PlanNode,
    result: ToolResultEnvelope,
    *,
    current_scene_revision: str | None,
) -> NodeSettlement:
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
        if result.scene_write_behavior == "new_revision" and (
            result.world_change_started is not True
            or not result.world_changed
            or result.new_scene_revision is None
        ):
            return NodeSettlement(
                **facts,
                status="failed",
                failure_code="missing_world_change_evidence",
            )
        if (
            result.world_changed
            and current_scene_revision is not None
            and result.new_scene_revision == current_scene_revision
        ):
            return NodeSettlement(**facts, status="stale", failure_code="scene_revision_not_advanced")
        missing = _missing_produced_evidence(node, result)
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
