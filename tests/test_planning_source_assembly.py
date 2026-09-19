"""Exercise compressed producer facts through real selection persistence and Query IO."""

import asyncio
import json
from copy import deepcopy

import pytest

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import (
    EvidenceExecutionContext,
    NodeExecutionContext,
    PlanningLoopError,
    node_source_page,
    resolve_node_argument_sources,
)
from PhyAgentOS.agent.prompt_context import _compact_forge_results
from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
from PhyAgentOS.agent.tools.planning import ForgePlanReadyTool, ForgePlanSelectTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GRASP_TOOL_SPEC
from PhyAgentOS.forge.task import AgentTaskCoordinator, ToolExecutionRecord
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanNode,
    ToolSpecPolicy,
    plan_graph_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


def producer():
    provenance = ["artifact://scene-1/capture/depth"]
    entities = [
        dict(
            entity_ref=f"entity://object-{i}",
            category=f"object {i}",
            confidence=0.98,
            provenance=provenance,
        )
        for i in range(5)
    ]
    envelopes = [
        dict(
            entity_ref=e["entity_ref"],
            frame_id="camera",
            unit="m",
            min_xyz_m=[i / 10, 0.1, 0.2],
            max_xyz_m=[i / 10 + 0.05, 0.15, 0.25],
            confidence=0.97,
            provenance=provenance,
        )
        for i, e in enumerate(entities)
    ]
    # Identity association must not rely on coincident array positions.
    return {
        "entities": entities,
        "spatial_envelopes": list(reversed(envelopes)),
        "scene_revision": "scene-1",
    }


def source_context():
    return NodeExecutionContext(
        task_id="task-assembly",
        revision_id="revision-assembly",
        node_id="grasp",
        capability="grasp.propose",
        dependencies=(),
        required_evidence=("tool:understanding",),
        input_bindings={},
        scene_revision="scene-1",
        evidence_context=(
            EvidenceExecutionContext(
                revision_id="discovery",
                record_id="understanding",
                tool_id="perception.inspect",
                status="succeeded",
                evidence_refs=("tool:understanding",),
                arguments={},
                response={"data": producer()},
            ),
        ),
    )


def source_map():
    result = {}
    for field in ("entity_ref", "category", "confidence"):
        result[field] = {
            "record_id": "understanding",
            "path": ["response", "data", "entities", 4, field],
            "target_path": ["targets", 0, field],
        }
    for field in GRASP_TOOL_SPEC["input_schema"]["properties"]["targets"]["items"]["properties"][
        "spatial_envelope"
    ]["properties"]:
        result["envelope_" + field] = {
            "record_id": "understanding",
            "path": ["response", "data", "spatial_envelopes", 0, field],
            "target_path": ["targets", 0, "spatial_envelope", field],
        }
    return result


def test_browse_all_entries_then_combine_exact_fields_without_mutating_producer():
    context = source_context()
    before = context.model_dump()
    page = node_source_page(context, "understanding", ["response", "data", "entities"], limit=3)
    assert page["next_offset"] == 3
    next_page = node_source_page(context, "understanding", page["path"], offset=3, limit=3)
    assert next_page["entries"][1]["identity"]["entity_ref"] == "entity://object-4"
    assert next_page["entries"][1]["path"][-1] == 4
    assert next_page["next_offset"] is None
    resolved = resolve_node_argument_sources(context, {}, source_map())
    target = resolved["targets"][0]
    assert target["entity_ref"] == "entity://object-4"
    assert target["spatial_envelope"]["min_xyz_m"] == [0.4, 0.1, 0.2]
    assert "provenance" not in target
    assert "entity_ref" not in target["spatial_envelope"]
    target["spatial_envelope"]["min_xyz_m"][0] = 999
    assert context.model_dump() == before


@pytest.mark.parametrize(
    "path",
    [
        ["response", "data", "entities", -1],
        ["response", "data", "entities", True],
        ["response", "data", "entities", "4"],
        ["response", "data", "entities", 10],
        ["response", "data", "entities", "*"],
        ["response", "absent"],
    ],
)
def test_invalid_source_paths_are_rejected(path):
    with pytest.raises(PlanningLoopError):
        resolve_node_argument_sources(
            source_context(), {}, {"x": {"record_id": "understanding", "path": path}}
        )


def test_conflicts_sparse_destinations_and_hidden_records_are_rejected():
    context = source_context()
    sources = source_map()
    with pytest.raises(PlanningLoopError, match="literal and sourced"):
        resolve_node_argument_sources(context, {"targets": [{"category": "invented"}]}, sources)
    overlap = deepcopy(sources)
    overlap["whole"] = {
        "record_id": "understanding",
        "path": ["response"],
        "target_path": ["targets"],
    }
    with pytest.raises(PlanningLoopError, match="overlap"):
        resolve_node_argument_sources(context, {}, overlap)
    sparse = {"one": {**sources["category"], "target_path": ["targets", 100000, "category"]}}
    with pytest.raises(PlanningLoopError, match="sparse"):
        resolve_node_argument_sources(context, {}, sparse)
    with pytest.raises(PlanningLoopError, match="not visible"):
        node_source_page(context, "other-task", [])


def test_cross_record_sources_and_array_order_are_explicit():
    context = source_context()
    extra = context.evidence_context[0].model_copy(
        update={
            "record_id": "other-visible",
            "response": {"data": {"label": "second"}},
        }
    )
    context = context.model_copy(update={"evidence_context": (*context.evidence_context, extra)})
    sources = {
        "second": {
            "record_id": "other-visible",
            "path": ["response", "data", "label"],
            "target_path": ["items", 1, "label"],
        },
        "first": {
            "record_id": "understanding",
            "path": ["response", "data", "entities", 4, "category"],
            "target_path": ["items", 0, "label"],
        },
    }
    assert resolve_node_argument_sources(context, {"items": []}, sources) == {
        "items": [{"label": "object 4"}, {"label": "second"}],
    }


def test_previous_catalog_pages_survive_prompt_compaction():
    context = source_context()
    pages = [
        node_source_page(context, "understanding", ["response", "data", field])
        for field in ("entities", "spatial_envelopes")
    ]
    messages = [
        {
            "role": "tool",
            "name": "forge_plan_ready",
            "content": json.dumps({"ok": True, "source_page": page}),
        }
        for page in pages
    ]
    for aggressive in (False, True):
        projected = _compact_forge_results(messages, aggressive=aggressive)
        assert [json.loads(m["content"])["source_page"] for m in projected] == pages


def test_schema_selection_receipt_and_query_execute_identical_assembled_values(
    tmp_path, monkeypatch
):
    calls = []

    class Client:
        async def invoke_query_tool(self, tool_id, arguments, **kwargs):
            calls.append((tool_id, deepcopy(arguments)))
            return {"ok": True, "data": {"status": "available", "candidates": []}}

    client = Client()
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=client)
    task = coordinator.create_task(
        task_description="assemble observed target",
        verification=TaskVerificationContract(mode="off"),
    )

    def seed(current):
        current.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="understanding",
                revision_id=current.active_revision_id,
                tool_id="perception.inspect",
                semantics="query",
                caller_id="test",
                status="succeeded",
                evidence_refs=["tool:understanding"],
                response={"ok": True, "data": producer()},
            )
        )

    coordinator.store.update(task.task_id, seed, event_type="test_discovery")
    node = PlanNode(
        node_id="grasp",
        obligation_id="grasp",
        capability="grasp.propose",
        required_evidence=("tool:understanding",),
    )
    payload = dict(
        task_id=task.task_id,
        revision_id="revision-assembly",
        graph_digest="0" * 64,
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
        nodes=[node.model_dump(mode="json")],
    )
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/assembly",
        discovery_evidence_refs=("tool:understanding",),
    )
    policy = ToolSpecPolicy(
        tool_id="grasp.propose",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("grasp.propose",),
    )
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"tool:understanding"})),
        input_schemas={"grasp.propose": GRASP_TOOL_SPEC["input_schema"]},
    )
    page = json.loads(
        asyncio.run(
            ForgePlanReadyTool(dispatch, coordinator).execute(
                node_id="grasp",
                source_record_id="understanding",
                source_path=["response", "data", "entities"],
                offset=3,
            )
        )
    )
    assert page["ok"] and len(page["source_page"]["entries"]) == 2

    def set_source_scene(current, scene):
        current.revisions[0].execution_records[0].response["data"]["scene_revision"] = scene

    coordinator.store.update(
        task.task_id,
        lambda current: set_source_scene(current, "old-scene"),
        event_type="test_stale_source",
    )
    stale_page = json.loads(
        asyncio.run(
            ForgePlanReadyTool(dispatch, coordinator).execute(
                node_id="grasp", source_record_id="understanding", source_path=["response", "data"]
            )
        )
    )
    assert stale_page["ok"] is False
    assert "stale scene" in stale_page["error"]["message"]
    assert calls == []
    coordinator.store.update(
        task.task_id,
        lambda current: set_source_scene(current, "scene-1"),
        event_type="test_restore_source",
    )
    arguments = dict(
        observation_ref="observation://scene-1/camera",
        scene_revision="scene-1",
        frame_id="camera",
        calibration_ref="artifact://scene-1/calibration",
        freshness_ms=0,
        max_age_ms=1000,
    )
    rejected = json.loads(
        asyncio.run(
            ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
                task.task_id,
                "grasp",
                "grasp.propose",
                arguments,
                "incompatible whole-array selection",
                {
                    "targets": {
                        "record_id": "understanding",
                        "path": ["response", "data", "entities"],
                    }
                },
            )
        )
    )
    assert rejected["error"]["code"] == "tool_input_schema_invalid"
    assert coordinator.get_task(task.task_id).active_revision.planning_selections == []
    assert coordinator.get_task(task.task_id).active_revision.execution_records == []
    assert calls == []
    selected = json.loads(
        asyncio.run(
            ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
                task.task_id,
                "grasp",
                "grasp.propose",
                arguments,
                "select observed object by identity",
                source_map(),
            )
        )
    )
    assert selected["ok"], selected
    assert calls == []
    receipt = selected["data"]
    assert receipt["selection"]["tool_arguments"] == {}
    assert receipt["selection"]["use_selected_arguments"] is True
    saved = (
        coordinator.get_task(task.task_id)
        .active_revision.planning_selections[0]
        .resumable_selection.tool_arguments
    )
    assert saved["targets"][0]["entity_ref"] == "entity://object-4"

    # Only the external binding/readiness lookup is replaced; persistence and execution are real.
    async def bound(*args):
        return BoundToolSpec(
            tool_id="grasp.propose", semantics="query", spec_sha256="3" * 64, ready_at_binding=True
        )

    monkeypatch.setattr(coordinator, "_require_binding_tool", bound)
    response = json.loads(
        asyncio.run(
            ForgeToolQueryTool(client, coordinator).execute(
                task_id=task.task_id,
                tool_id="grasp.propose",
                arguments={},
                planning_binding=receipt["planning_binding"],
                use_selected_arguments=True,
            )
        )
    )
    assert response["ok"], response
    assert calls == [("grasp.propose", saved)]
    records = coordinator.get_task(task.task_id).active_revision.execution_records
    assert len(records) == 1 and records[0].node_id == "grasp"
