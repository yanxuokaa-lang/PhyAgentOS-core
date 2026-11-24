from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import (
    AgentTaskCoordinator,
    AgentTaskRecord,
    AgentTaskStatus,
    PlanRevision,
    ToolExecutionRecord,
)
from PhyAgentOS.planning import NodeSettlement, PlanGraph, PlanNode, plan_graph_digest, plan_node_digest
from PhyAgentOS.verification.contracts import TaskVerificationContract


def _revision(number):
    revision_id = f"revision-{number}"
    invocation = f"invocation://pour/{number}"
    phases = [
        ("manipulation.prepare", "prepare"),
        ("object.acquire", "acquire"),
        ("manipulation.prepare_held", "prepare"),
        ("object.pour", "process"),
        ("manipulation.prepare_held", "prepare"),
        ("object.place", "place"),
    ]
    arguments = {
        "subtask_id": "pour-r05",
        "operation": "pour",
        "parameters": {"tilt_rad": 1.0, "hold_s": 2},
        "return_destination_ref": "destination://rack/r05",
        "binding": {
            "category": "bottle",
            "destination_category": "vessel",
            "entity_ref": f"entity://r05-{number}",
            "semantic_label": "R05",
            "destination_ref": f"destination://beaker-{number}",
            "destination_semantic_label": "BEAKER",
            "scene_revision": f"scene-{number}",
        },
        "tool_sequence": [{"tool_id": tool, "phase": phase} for tool, phase in phases],
    }
    node = PlanNode(node_id="pour-r05", capability="manipulation.execute_subtask",
                    obligation_id="pour-r05", input_bindings=arguments)
    graph_payload = {
        "task_id": "task", "revision_id": revision_id, "nodes": [node.model_dump(mode="json")],
        "planner_decision_digest": "a" * 64, "policy_snapshot_digest": "b" * 64,
    }
    graph = PlanGraph.model_validate({**graph_payload, "graph_digest": plan_graph_digest(graph_payload)})
    failed = number == 1
    observed = {
        "status": "failed" if failed else "succeeded",
        "outcome_known": True, "world_change_started": True, "possession_state": "empty",
        "new_scene_revision": f"scene-{number + 1}",
        "requires_replan": failed, "failure_owner": "execution" if failed else "none",
        "retryable_in_revision": False,
    }
    if failed:
        observed.update({
            "object_support_state": "on_support",
            "returned_to_safe_pose": True,
            "observation_ready": True,
            "recommended_action": "refresh_perception_before_motion",
        })
    receipts = [
        {"tool_id": tool, "phase": phase, "outcome_known": True,
         "status": "available" if phase == "prepare" else observed["status"]}
        for tool, phase in (phases[:2] if failed else phases)
    ]
    if failed:
        receipts[-1]["response"] = observed.copy()
    response = {"data": {"result": {**observed, "subtask_result": {
        "subtask_id": "pour-r05", "status": "failed" if failed else "completed",
        "outcome_known": True, "failed_phase": "acquire" if failed else None,
        "completed_tool_ids": [tool for tool, _ in (phases[:1] if failed else phases)],
        "receipts": receipts,
    }}}}
    record = ToolExecutionRecord(
        record_id=f"record-{number}", revision_id=revision_id,
        tool_id=node.capability, semantics="action", caller_id="agent",
        node_id=node.node_id, obligation_id=node.obligation_id, node_digest=plan_node_digest(node),
        input_binding_digest="c" * 64, decision_trace_ref=f"artifact://trace/{number}",
        invocation_id=invocation, arguments=deepcopy(arguments),
        status=observed["status"], response=response, evidence_refs=[invocation],
    )
    settlement = NodeSettlement(
        task_id=graph.task_id, revision_id=revision_id, node_id=node.node_id,
        status="failed" if failed else "completed", invocation_id=invocation,
        world_change_started=True, outcome_known=True, requires_replan=failed,
        source_tool_id=record.tool_id,
    )
    return PlanRevision(
        revision_id=revision_id, number=number, reason="Persisted subtask execution",
        plan_graph=graph, plan_graph_ref=f"artifact://plans/{number}", plan_graph_digest=graph.graph_digest,
        planner_decision_digest=graph.planner_decision_digest, policy_snapshot_digest=graph.policy_snapshot_digest,
        execution_records=[record], node_settlements=[settlement],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("change,expected", [
    ("none", AgentTaskStatus.SUCCEEDED),
    ("unlabeled-same-entities", AgentTaskStatus.SUCCEEDED),
    ("unknown", AgentTaskStatus.FAILED),
    ("unsafe", AgentTaskStatus.FAILED),
    ("partial-process", AgentTaskStatus.FAILED),
    ("different-source", AgentTaskStatus.FAILED),
    ("different-destination", AgentTaskStatus.FAILED),
    ("different-request", AgentTaskStatus.FAILED),
    ("different-return", AgentTaskStatus.FAILED),
    ("different-obligation", AgentTaskStatus.FAILED),
    ("same-invocation", AgentTaskStatus.FAILED),
    ("unmatched-settlement", AgentTaskStatus.FAILED),
    ("incomplete-success", AgentTaskStatus.FAILED),
    ("other-failed-query", AgentTaskStatus.FAILED),
])
async def test_finalization_requires_a_measured_replacement_of_a_safely_recovered_acquire(tmp_path, change, expected):
    first, later = _revision(1), _revision(2)
    failed, successor = first.execution_records[0], later.execution_records[0]
    failure = failed.response["data"]["result"]
    completed = successor.response["data"]["result"]["subtask_result"]
    if change == "unlabeled-same-entities":
        for label_key, ref_key in [
            ("semantic_label", "entity_ref"), ("destination_semantic_label", "destination_ref"),
        ]:
            failed.arguments["binding"].pop(label_key)
            successor.arguments["binding"].pop(label_key)
            successor.arguments["binding"][ref_key] = failed.arguments["binding"][ref_key]
    elif change == "unknown":
        failed.status = "unknown"
        failure["outcome_known"] = False
    elif change == "unsafe":
        failure["observation_ready"] = False
    elif change == "partial-process":
        failure["subtask_result"]["completed_tool_ids"].append("object.pour")
    elif change == "different-source":
        successor.arguments["binding"]["semantic_label"] = "R03"
    elif change == "different-destination":
        successor.arguments["binding"]["destination_semantic_label"] = "OTHER"
    elif change == "different-request":
        successor.arguments["parameters"]["hold_s"] = 3
    elif change == "different-return":
        successor.arguments["return_destination_ref"] = "destination://rack/r03"
    elif change == "different-obligation":
        successor.obligation_id = "another-pour"
    elif change == "same-invocation":
        successor.invocation_id = failed.invocation_id
        later.node_settlements[0] = later.node_settlements[0].model_copy(
            update={"invocation_id": failed.invocation_id}
        )
    elif change == "unmatched-settlement":
        later.node_settlements[0] = later.node_settlements[0].model_copy(
            update={"invocation_id": "invocation://other"}
        )
    elif change == "incomplete-success":
        completed["receipts"][3]["outcome_known"] = False
    elif change == "other-failed-query":
        first.execution_records.append(ToolExecutionRecord(
            record_id="failed-query", revision_id=first.revision_id,
            tool_id="scene.observe", semantics="query", caller_id="agent", status="failed",
        ))

    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=None)
    coordinator._capture_after = AsyncMock()
    task = AgentTaskRecord(
        task_id="task", task_description="Pour R05 into the beaker and return it",
        verification=TaskVerificationContract(mode="off"), revisions=[first, later],
        active_revision_id=later.revision_id,
    )
    coordinator.store.create(task)

    finalized = await coordinator.finalize_task(task.task_id)

    assert finalized.status == expected
    assert finalized.execution_records == task.execution_records
    assert finalized.revisions[0].node_settlements == first.node_settlements
    assert coordinator.store.events(task.task_id)[-1]["event_type"] == "task_finalized_from_execution"
