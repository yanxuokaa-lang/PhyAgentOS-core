"""Trusted manipulation inputs derived from bounded Coordinator Query records."""
from collections.abc import Mapping
from copy import deepcopy

from PhyAgentOS.forge.manipulation import MANIPULATION_INTENT_SEMANTIC_KEYS, ManipulationIntent
from PhyAgentOS.planning import plan_node_digest


def direct_query_results(context):
    """Select unambiguous successful Queries from completed direct predecessors."""
    results = {}
    for predecessor in context.predecessor_context:
        if predecessor.status != "completed":
            raise ValueError("relation predecessor is not completed")
        if predecessor.scene_revision not in (None, context.scene_revision):
            raise ValueError("relation predecessor scene is stale")
        for record in predecessor.executions:
            if record.semantics != "query" or record.status != "succeeded":
                continue
            response = record.response
            data = response.get("data") if isinstance(response, Mapping) else None
            if not isinstance(data, Mapping) or data.get("status") != "available":
                raise ValueError("relation predecessor Query is unavailable")
            if record.tool_id in results:
                raise ValueError("relation predecessor Query is ambiguous")
            results[record.tool_id] = {"arguments": deepcopy(record.arguments), "result": deepcopy(dict(data))}
    return results


def relation_manipulation_intent(graph, node, context):
    if (context.task_id != graph.task_id or context.revision_id != graph.revision_id
            or context.node_id != node.node_id or tuple(context.dependencies) != tuple(node.dependencies)):
        raise ValueError("relation context is not bound to the active node")
    semantic = node.input_bindings.get("semantic_intent")
    if not isinstance(semantic, Mapping) or set(semantic) - MANIPULATION_INTENT_SEMANTIC_KEYS:
        raise ValueError("relation node requires structured semantic intent")
    identity = node.input_bindings
    if context.scene_revision != identity.get("scene_revision"):
        raise ValueError("relation node scene differs from current context")
    grasp_record = direct_query_results(context).get("grasp.propose")
    grasp = grasp_record["result"] if grasp_record else None
    if not isinstance(grasp, Mapping):
        raise ValueError("relation node requires a direct grasp Query")
    for key in ("scene_revision", "observation_ref", "calibration_ref"):
        if grasp.get(key) != identity.get(key):
            raise ValueError("grasp Query identity differs from relation node")
    if grasp.get("frame", {}).get("frame_id") != identity.get("observation_frame_id"):
        raise ValueError("grasp Query frame differs from relation node")
    candidates = grasp.get("candidates")
    if not isinstance(candidates, list) or not candidates or any(
        not isinstance(item, Mapping) or item.get("entity_ref") != identity.get("entity_ref")
        for item in candidates
    ):
        raise ValueError("grasp Query candidates differ from relation entity")
    return ManipulationIntent.model_validate({
        **semantic, "task_id": graph.task_id, "revision_id": graph.revision_id,
        "node_id": node.node_id, "node_digest": plan_node_digest(node),
        **{key: identity[key] for key in ("entity_ref", "scene_revision", "observation_ref",
                                        "observation_frame_id", "calibration_ref")},
        "candidate_set_ref": grasp["candidate_set_ref"], "motion_authorized": False,
    })
