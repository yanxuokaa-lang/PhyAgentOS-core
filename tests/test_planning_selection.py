from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import PhyAgentOS.forge.task as forge_task_module
from PhyAgentOS.agent.plan_proposal import _complete_persisted_runtime_bindings
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import PlanningLoopError
from PhyAgentOS.agent.tools.planning import (
    ForgePlanSelectTool,
    _merge_projection_compatible_sources,
)
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GRASP_TOOL_SPEC
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError, AgentTaskStatus
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ToolSpecPolicy,
    canonical_sha256,
    plan_graph_digest,
    plan_node_digest,
    project_tool_spec,
    tool_input_binding_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


def test_oracle_destination_compiles_agent_entity_label_from_scene_bind():
    grasp = PlanNode(
        node_id="red.grasp",
        obligation_id="red.grasp",
        capability="grasp.propose",
        input_bindings={"entity_ref": "entity://red-block-1"},
    )
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        dependencies=("red.grasp",),
        input_bindings={
            "entity_ref": "entity://red-block-1",
            "destination_ref": "destination://blocks-ranking-rgb/red-slot",
        },
    )

    def record(tool_id, response):
        return SimpleNamespace(
            record_id=f"record-{tool_id}", node_id=None, tool_id=tool_id,
            status="succeeded", response=response,
        )

    revision = SimpleNamespace(execution_records=(
        record("scene.bind", {"data": {"entities": [{
            "entity_ref": "entity://block-red-01",
            "execution_entity_ref": "entity://block-red-1",
        }]} }),
        record("task.goal", {"data": {
            "goal_source": "benchmark_task_definition",
            "goals": [{
                "execution_entity_ref": "entity://block-red-1",
                "destination_ref": "destination://blocks-ranking-rgb/red-slot",
            }],
        }}),
    ))
    task = SimpleNamespace(active_revision=revision, revisions=(revision,))

    completed = _complete_persisted_runtime_bindings(task, (grasp, prepare))

    assert completed[0].input_bindings["entity_ref"] == "entity://block-red-01"
    assert completed[1].input_bindings["entity_ref"] == "entity://block-red-01"


class _Coordinator:
    def __init__(self):
        self.proposals = []
        self.rejections = []

    def persist_planning_selection(self, proposal):
        self.proposals.append(proposal)
        return {
            "node_id": proposal["node_id"],
            "node_digest": proposal["node_digest"],
            "obligation_id": "observe",
            "input_binding_digest": proposal["input_binding_digest"],
            "decision_trace_ref": "artifact://planning-traces/task-1/revision-1/observe/t1",
            "task_id": proposal["task_id"],
            "revision_id": proposal["revision_id"],
            "scene_revision": proposal["scene_revision"],
            "tool_arguments": proposal["tool_arguments"],
        }

    def record_planning_selection_rejection(self, task_id, **kwargs):
        self.rejections.append((task_id, kwargs))


class _Dispatch:
    graph = SimpleNamespace(task_id="task-1", revision_id="revision-1")
    current_scene_revision = "scene-1"

    def argument_projection(self, tool_id):
        return None, None

    def prepare_selection(self, **kwargs):
        return {
            "task_id": "task-1",
            "revision_id": "revision-1",
            "node_id": kwargs["node_id"],
            "node_digest": "1" * 64,
            "obligation_id": "observe",
            "tool_id": kwargs["tool_id"],
            "candidate_tool_ids": (kwargs["tool_id"],),
            "input_binding_digest": "2" * 64,
            "scene_revision": "scene-1",
            "evidence_refs": (),
            "decision_reason": kwargs["decision_reason"],
            "tool_arguments": kwargs["arguments"],
        }


def test_plan_select_is_control_plane_only_and_returns_binding():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: _Dispatch())

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is True
    assert result["motion_authorized"] is False
    assert result["data"]["planning_binding"]["decision_trace_ref"].startswith("artifact://")
    assert "scene_revision" not in result["data"]["planning_binding"]
    assert result["data"]["selection"]["scene_revision"] == "scene-1"
    assert result["data"]["selection"]["tool_arguments"] == {}
    assert coordinator.proposals[0]["tool_id"] == "scene.observe"


def test_plan_select_resumes_existing_unconsumed_selection_without_reselecting():
    class Coordinator(_Coordinator):
        def pending_planning_selection(self, task_id, node_id, *, scene_revision):
            assert (task_id, node_id, scene_revision) == ("task-1", "observe", "scene-1")
            return {
                "task_id": task_id,
                "revision_id": "revision-1",
                "node_id": node_id,
                "scene_revision": scene_revision,
                "execution_tool": "forge_tool_query",
                "tool_id": "scene.observe",
                "arguments": {"sensor_ref": "head_camera", "max_age_ms": 1000},
                "planning_binding": {
                    "revision_id": "revision-1",
                    "node_id": node_id,
                    "node_digest": "1" * 64,
                    "obligation_id": "observe",
                    "input_binding_digest": "2" * 64,
                    "decision_trace_ref": "artifact://planning-traces/task-1/revision-1/observe/t1",
                },
            }

    coordinator = Coordinator()
    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: _Dispatch()
    ).execute(
        "task-1", "observe", "scene.observe", {"sensor_ref": "wrong"}, "retry selection"
    )))

    assert result["ok"] is True
    assert result["data"]["resumed_selection"] is True
    assert result["data"]["selection"]["use_selected_arguments"] is True
    assert result["data"]["selection"]["arguments"] == {}
    assert coordinator.proposals == []


@pytest.mark.parametrize("candidates", [
    [{"candidate_ref": "candidate://green/1", "score": 0.9}],
    [{"candidate_ref": "candidate://green/2", "score": 0.7},
     {"candidate_ref": "candidate://green/3", "score": 0.8}],
    [],
])
def test_plan_select_resolves_catalogued_predecessor_source_before_persistence(candidates):
    predecessor = PlanNode(
        node_id="propose",
        obligation_id="propose",
        capability="grasp.propose",
    )
    consumer = PlanNode(
        node_id="prepare",
        obligation_id="prepare",
        capability="manipulation.prepare",
        dependencies=("propose",),
    )
    graph_payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [
            predecessor.model_dump(mode="json"),
            consumer.model_dump(mode="json"),
        ],
    }
    graph_payload["graph_digest"] = plan_graph_digest(graph_payload)
    graph = PlanGraph.model_validate(graph_payload)
    task = SimpleNamespace(
        task_id="task-1",
        primary_skill_binding=None,
        tool_bindings=(),
        revisions=(),
        active_revision=SimpleNamespace(
            revision_id="revision-1",
            plan_graph=graph,
            node_settlements=(
                SimpleNamespace(
                    node_id="propose",
                    status="completed",
                    scene_revision="scene-1",
                    evidence_refs=("tool:proposal",),
                    source_tool_id="grasp.propose",
                    failure_code=None,
                ),
            ),
            execution_records=(
                SimpleNamespace(
                    record_id="tool-proposal",
                    node_id="propose",
                    tool_id="grasp.propose",
                    semantics="query",
                    status="succeeded",
                    arguments={"entity_ref": "entity://green"},
                    response={"data": {"candidates": candidates}},
                    error=None,
                ),
            ),
            discovery_evidence_refs=(),
            fresh_evidence_requirements=(),
            replan_evidence_refs=(),
        ),
    )

    class Coordinator(_Coordinator):
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

    coordinator = Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: _Dispatch())
    wrong_mode = json.loads(asyncio.run(tool.execute(
        "task-1", "prepare", "manipulation.prepare", {"entity_ref": "entity://green"},
        "use persisted proposal", projection_source={"record_id": "tool-proposal"},
    )))
    assert wrong_mode["error"]["code"] == "consumer_projection_invalid"
    assert wrong_mode["error"]["retryable_in_revision"] is True
    assert wrong_mode["error"]["requires_replan"] is False
    assert coordinator.proposals == []

    hidden_source = json.loads(asyncio.run(tool.execute(
        "task-1", "prepare", "manipulation.prepare", {"entity_ref": "entity://green"},
        "use persisted proposal", argument_sources={
            "candidates": {"record_id": "unrelated-record", "path": ["response", "data", "candidates"]},
        },
    )))
    assert hidden_source["error"]["code"] == "invalid_argument_source"
    assert hidden_source["error"]["requires_replan"] is False
    assert coordinator.proposals == []

    result = json.loads(
        asyncio.run(
            tool.execute(
                "task-1",
                "prepare",
                "manipulation.prepare",
                {"entity_ref": "entity://green"},
                "use persisted proposal",
                {
                    "candidates": {
                        "record_id": "tool-proposal",
                        "path": ["response", "data", "candidates"],
                    }
                },
            )
        )
    )

    assert result["ok"] is True
    assert coordinator.proposals[0]["tool_arguments"] == {
        "entity_ref": "entity://green",
        "candidates": candidates,
    }
    assert result["data"]["selection"]["tool_arguments"] == {}
    assert result["data"]["selection"]["use_selected_arguments"] is True


def test_plan_select_projects_authorized_understanding_into_persisted_consumer_arguments():
    evidence_ref = "artifact://scene-1/understanding"
    node = PlanNode(
        node_id="grasp-green",
        obligation_id="grasp-green",
        capability="grasp.propose",
        required_evidence=(evidence_ref,),
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    understanding_arguments = {
        "observation_ref": "observation://scene-1/head",
        "scene_revision": "scene-1",
        "frame_id": "head_camera",
        "calibration_ref": "artifact://scene-1/calibration/head",
        "freshness_ms": 10,
        "max_age_ms": 1000,
    }
    understanding_response = {"data": {
        "entities": [{
            "entity_ref": "entity://green", "category": "green block", "confidence": 0.98,
        }],
        "spatial_envelopes": [{
            "entity_ref": "entity://green", "frame_id": "head_camera", "unit": "m",
            "min_xyz_m": [0.1, 0.2, 0.3], "max_xyz_m": [0.2, 0.3, 0.4],
            "confidence": 0.91, "provenance": ["artifact://scene-1/depth/head"],
        }],
        "derived_artifacts": [{
            "artifact_ref": "artifact://scene-1/cloud/green", "kind": "object_point_cloud",
            "observation_ref": "observation://scene-1/head", "scene_revision": "scene-1",
            "entity_ref": "entity://green", "frame_id": "head_camera",
            "calibration_ref": "artifact://scene-1/calibration/head",
            "provenance": ["artifact://scene-1/depth/head"],
            "descriptor": {"producer_only": True},
        }],
    }}
    record = SimpleNamespace(
        record_id="understanding-record",
        node_id=None,
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        evidence_refs=(evidence_ref,),
        arguments=understanding_arguments,
        response=understanding_response,
        error=None,
    )
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=graph,
        node_settlements=(),
        execution_records=(record,),
        discovery_evidence_refs=(evidence_ref,),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    task = SimpleNamespace(
        task_id="task-1",
        primary_skill_binding=None,
        tool_bindings=(),
        revisions=(revision,),
        active_revision=revision,
    )

    class Coordinator(_Coordinator):
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        def persist_planning_selection(self, proposal):
            self.proposals.append(proposal)
            return {
                **proposal,
                "decision_trace_ref": "artifact://planning-traces/task-1/revision-1/grasp-green/t1",
            }

    coordinator = Coordinator()
    dispatch = AgentComposedDispatch(
        graph,
        (project_tool_spec(GRASP_TOOL_SPEC),),
        AdmissionContext(scene_revision="scene-1", evidence_refs=(evidence_ref,)),
        input_schemas={"grasp.propose": GRASP_TOOL_SPEC["input_schema"]},
    )
    assert dispatch.describe()["ready_nodes"][0]["selection_source_modes"] == {
        "grasp.propose": "projection_source"
    }
    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        "task-1",
        "grasp-green",
        "grasp.propose",
        {},
        "select the current green entity",
        argument_sources={
            "observation_ref": {
                "record_id": "understanding-record",
                "path": ["arguments", "observation_ref"],
            },
        },
        projection_source={"record_id": "understanding-record"},
    )))

    assert result["ok"] is True
    assert result["motion_authorized"] is False
    assert result["data"]["selection"] == {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "scene_revision": "scene-1",
        "tool_arguments": {},
        "use_selected_arguments": True,
    }
    persisted = coordinator.proposals[0]["tool_arguments"]
    assert persisted["targets"][0]["entity_ref"] == "entity://green"
    assert persisted["targets"][0]["spatial_envelope"]["min_xyz_m"] == [0.1, 0.2, 0.3]
    assert "entity_ref" not in persisted["targets"][0]["spatial_envelope"]
    assert "descriptor" not in persisted["targets"][0]["geometry_artifacts"][0]

    conflict = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        "task-1",
        "grasp-green",
        "grasp.propose",
        {"entity_ref": "entity://renamed-green"},
        "reject a renamed entity",
        projection_source={"record_id": "understanding-record"},
    )))
    assert conflict["ok"] is False
    assert conflict["error"]["code"] == "semantic_binding_mismatch"
    assert len(coordinator.proposals) == 1


def test_projection_rejects_cross_record_legacy_sources():
    context = SimpleNamespace(
        predecessor_context=(),
        evidence_context=(
            SimpleNamespace(
                record_id="understanding-record",
                status="succeeded",
                arguments={"observation_ref": "observation://scene-1/head"},
                response={"data": {}},
            ),
        ),
    )
    plan = SimpleNamespace(top_level_fields=("observation_ref",))

    with pytest.raises(PlanningLoopError, match="same authorized record"):
        _merge_projection_compatible_sources(
            context,
            literals={},
            argument_sources={
                "observation_ref": {
                    "record_id": "other-record",
                    "path": ["arguments", "observation_ref"],
                },
            },
            projection_source={"record_id": "understanding-record"},
            projection_plan=plan,
        )


def test_projection_rejects_nested_legacy_target_override():
    context = SimpleNamespace(predecessor_context=(), evidence_context=())
    plan = SimpleNamespace(top_level_fields=("observation_ref",))

    with pytest.raises(PlanningLoopError, match="only declared top-level source fields"):
        _merge_projection_compatible_sources(
            context,
            literals={},
            argument_sources={
                "observation_ref": {
                    "record_id": "understanding-record",
                    "path": ["arguments", "observation_ref"],
                    "target_path": ["targets", 0, "observation_ref"],
                },
            },
            projection_source={"record_id": "understanding-record"},
            projection_plan=plan,
        )


def test_plan_select_rejects_when_task_is_not_active_graph():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: None)

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "inactive_plan_graph"
    assert result["error"]["recommended_action"] == "activate_current_task_plan"
    assert result["error"]["rejection_persisted"] is True
    assert coordinator.proposals == []


def test_plan_select_reports_rejection_persistence_failure():
    class FailingCoordinator(_Coordinator):
        def record_planning_selection_rejection(self, task_id, **kwargs):
            raise RuntimeError("task event store unavailable")

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        FailingCoordinator(), lambda: None
    ).execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "inactive_plan_graph"
    assert result["error"]["rejection_persisted"] is False
    persistence = result["error"]["persistence_error"]
    assert persistence == {
        "type": "RuntimeError",
        "code": "planning_selection_rejection_not_persisted",
        "failure_owner": "coordinator",
        "message": "task event store unavailable",
        "recommended_action": "read_authoritative_task_state",
    }


def test_replan_budget_exhaustion_runs_terminal_cleanup(tmp_path):
    class Experience:
        def __init__(self):
            self.completed = []

        def schedule_forge_completion(self, task_id):
            self.completed.append(task_id)

    binding_id = "runtime-binding-budget-exhausted"
    experience = Experience()
    task_bindings = {binding_id}
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
        experience=experience,
        runtime_task_binding_ids=task_bindings,
        max_replans=0,
    )
    task = coordinator.create_task(
        task_description="reject an unbindable historical plan",
        verification=TaskVerificationContract(mode="off"),
    )
    task_id = task.task_id

    def attach_runtime_binding(current):
        current.runtime_binding = RuntimeBinding(
            binding_id=binding_id,
            runtime_profile="fake",
            runtime_instance_id="runtime-budget-exhausted",
            gateway_url="http://fake",
        )
        current.active_revision.runtime_binding_id = binding_id

    coordinator.store.update(
        task_id,
        attach_runtime_binding,
        event_type="test_runtime_binding",
    )

    result = coordinator.record_planning_selection_rejection(
        task_id,
        revision_id=task.active_revision_id,
        node_id="acquire-blue",
        tool_id="object.acquire",
        error={
            "type": "PlanningDispatchError",
            "code": "node_tool_binding_incompatible",
            "failure_owner": "plan_graph",
            "message": "entity_ref is not frozen",
            "retryable_in_revision": False,
            "requires_replan": True,
            "recommended_action": "replace_active_plan_graph",
        },
    )

    assert result.status == AgentTaskStatus.FAILED
    assert binding_id not in task_bindings
    assert experience.completed == [task_id]
    assert result.execution_records == []


def test_correctable_selection_rejection_keeps_real_task_executing(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object(), max_replans=0,
    )
    task = coordinator.create_task(
        task_description="prepare a currently observed block",
        verification=TaskVerificationContract(mode="off"),
    )
    result = coordinator.record_planning_selection_rejection(
        task.task_id,
        revision_id=task.active_revision_id,
        node_id="prepare",
        tool_id="manipulation.prepare",
        error={
            "code": "consumer_projection_invalid",
            "failure_owner": "agent_arguments",
            "message": "projection_source requires a declared projection",
            "retryable_in_revision": True,
            "requires_replan": False,
            "recommended_action": "use_argument_sources_for_this_consumer",
        },
    )
    assert result.status == AgentTaskStatus.EXECUTING
    assert result.execution_records == []
    assert coordinator.planning_selection_rejections(
        task.task_id, task.active_revision_id, "prepare"
    )[-1]["code"] == "consumer_projection_invalid"


def test_missing_node_source_context_requires_plan_recovery():
    class Coordinator(_Coordinator):
        def get_task(self, _task_id):
            return SimpleNamespace(
                active_revision=SimpleNamespace(plan_graph=None),
            )

    coordinator = Coordinator()
    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: _Dispatch()
    ).execute(
        "task-1", "prepare", "manipulation.prepare", {}, "copy predecessor candidates",
        argument_sources={
            "candidates": {"record_id": "tool-proposal", "path": ["response", "data", "candidates"]},
        },
    )))
    assert result["error"]["code"] == "source_context_invalid"
    assert result["error"]["retryable_in_revision"] is False
    assert result["error"]["requires_replan"] is True
    assert coordinator.proposals == []


def test_prepare_selection_reports_all_missing_runtime_arguments_and_persists_event(tmp_path):
    task_id = "task-missing-candidates"
    revision_id = "revision-missing-candidates"
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
            "goal": "prepare green",
            "success_criteria": ["one prepared candidate"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
        },
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="manipulation.prepare",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("manipulation.prepare",),
        trusted_argument_builder="manipulation_intent_v2",
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="prepare green",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )
    tool = ForgePlanSelectTool(coordinator, lambda: dispatch)

    result = json.loads(asyncio.run(tool.execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {},
        "prepare current candidates",
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "missing_runtime_arguments"
    assert result["error"]["failure_owner"] == "agent_arguments"
    assert result["error"]["retryable_in_revision"] is True
    assert result["error"]["requires_replan"] is False
    assert result["error"]["task_status"] == "executing"
    assert set(result["error"]["missing_fields"]) == {
        "observation_ref",
        "scene_revision",
        "frame_id",
        "calibration_ref",
        "freshness_ms",
        "max_age_ms",
        "candidate_set_ref",
        "candidates",
    }
    current = coordinator.get_task(task_id)
    assert current.execution_records == []
    rejection = coordinator.store.events(task_id)[-1]
    assert rejection["event_type"] == "planning_selection_rejected"
    assert rejection["payload"]["error"]["code"] == "missing_runtime_arguments"
    assert "arguments" not in rejection["payload"]
    assert rejection["payload"]["motion_authorized"] is False


def test_incomplete_grasp_selection_is_rejected_before_tool_record(tmp_path):
    task_id = "task-incomplete-grasp"
    revision_id = "revision-incomplete-grasp"
    node = PlanNode(
        node_id="grasp-green",
        obligation_id="grasp-green",
        capability="grasp.propose",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
        },
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="grasp.propose",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("grasp.propose",),
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="propose a grasp for green",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(scene_revision="scene-1"),
        input_schemas={"grasp.propose": GRASP_TOOL_SPEC["input_schema"]},
    )

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {"entity_ref": "entity://green"},
        "select the current green entity",
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "tool_input_schema_invalid"
    assert "targets" in result["error"]["missing_fields"]
    assert coordinator.get_task(task_id).execution_records == []
    event = coordinator.store.events(task_id)[-1]
    assert event["event_type"] == "planning_selection_rejected"
    assert event["payload"]["motion_authorized"] is False


def test_unbindable_historical_selection_enters_bounded_replan(tmp_path):
    task_id = "task-historical-unbindable"
    revision_id = "revision-historical-unbindable"
    node = PlanNode(
        node_id="acquire-blue",
        obligation_id="acquire-blue",
        capability="object.acquire",
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="object.acquire",
        semantics="action",
        spec_digest="3" * 64,
        capabilities=("object.acquire",),
        input_binding_keys=("entity_ref",),
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="resume a historical graph",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {},
        "select historical node",
    )))

    assert result["error"]["code"] == "node_tool_binding_incompatible"
    assert result["error"]["requires_replan"] is True
    assert result["error"]["retryable_in_revision"] is False
    assert result["error"]["task_status"] == "awaiting_replan"
    current = coordinator.get_task(task_id)
    assert current.status.value == "awaiting_replan"
    assert current.replan_deadline is not None
    assert current.execution_records == []
    assert coordinator.store.events(task_id)[-1]["event_type"] == "planning_selection_rejected"


def test_real_coordinator_persists_context_bound_decision_trace(tmp_path, monkeypatch):
    task_id = "task-real-selection"
    revision_id = "revision-real-selection"
    node = PlanNode(node_id="observe", obligation_id="observe", capability="scene.observe")
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    coordinator.create_task(
        task_description="observe",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-real-selection/revision-real-selection",
    )
    policy = ToolSpecPolicy(
        tool_id="scene.observe",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.observe",),
    )
    context = AdmissionContext(scene_revision="scene-real")
    dispatch = AgentComposedDispatch(graph, (policy,), context)
    proposal = dispatch.prepare_selection(
        node_id="observe",
        tool_id="scene.observe",
        arguments={},
        decision_reason="initial observation",
    )
    atomic_write = forge_task_module.atomic_write_text
    write_attempts = 0

    def fail_first_trace_write(*args, **kwargs):
        nonlocal write_attempts
        write_attempts += 1
        if write_attempts == 1:
            raise OSError("simulated trace write failure")
        return atomic_write(*args, **kwargs)

    monkeypatch.setattr(forge_task_module, "atomic_write_text", fail_first_trace_write)
    with pytest.raises(OSError, match="simulated trace write failure"):
        coordinator.persist_planning_selection(proposal)
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    binding = coordinator.persist_planning_selection(proposal)
    assert write_attempts == 2
    duplicate = coordinator.persist_planning_selection(proposal)
    assert duplicate["decision_trace_ref"] == binding["decision_trace_ref"]
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    monkeypatch.setattr(coordinator, "pending_planning_selection", lambda *_args, **_kwargs: None)
    concurrent_retry = coordinator.persist_planning_selection(proposal)
    monkeypatch.undo()
    assert concurrent_retry["decision_trace_ref"] == binding["decision_trace_ref"]
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    different = dispatch.prepare_selection(
        node_id="observe",
        tool_id="scene.observe",
        arguments={"max_age_ms": 1000},
        decision_reason="different accepted input",
    )
    with pytest.raises(AgentTaskError, match="unconsumed selection"):
        coordinator.persist_planning_selection(different)
    validated = PlanningExecutionBinding.model_validate(
        {key: binding[key] for key in PlanningExecutionBinding.model_fields}
    )
    assert validated.revision_id == revision_id
    assert validated.node_id == "observe"
    saved_arguments = coordinator.selected_execution_arguments(
        task_id, "scene.observe", "query", {}, validated.model_dump(mode="json")
    )
    assert saved_arguments == {}
    corrupted = validated.model_copy(update={"input_binding_digest": "f" * 64})
    assert coordinator.selected_execution_arguments(
        task_id, "scene.observe", "query", {}, corrupted.model_dump(mode="json")
    ) == {}
    with pytest.raises(AgentTaskError, match="no matching unconsumed selection"):
        coordinator.selected_execution_arguments(
            task_id, "other.query", "query", {}, validated.model_dump(mode="json")
        )
    with pytest.raises(AgentTaskError, match="empty literal"):
        coordinator.selected_execution_arguments(
            task_id, "scene.observe", "query", {"changed": True}, validated.model_dump(mode="json")
        )
    trace_path = tmp_path / "artifacts" / "planning-traces" / task_id / revision_id / "observe"
    traces = list(trace_path.glob("*.json"))
    assert len(traces) == 1
    trace = json.loads(traces[0].read_text())
    assert trace["context_digest"] == canonical_sha256(context.model_dump(mode="json"))
    assert trace["selected_tool_id"] == "scene.observe"
    resumable = trace["resumable_selection"]
    assert resumable["tool_id"] == "scene.observe"
    assert resumable["semantics"] == "query"
    assert resumable["tool_arguments"] == {}
    assert resumable["planning_binding"]["decision_trace_ref"] == binding["decision_trace_ref"]
    assert binding["tool_arguments"] == {}
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-real"
    ) == {
        "task_id": task_id,
        "revision_id": revision_id,
        "node_id": "observe",
        "scene_revision": "scene-real",
        "execution_tool": "forge_tool_query",
        "tool_id": "scene.observe",
        "arguments": {},
        "planning_binding": validated.model_dump(mode="json"),
    }
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-stale"
    ) is None

    selected_tool = BoundToolSpec(
        tool_id="scene.observe",
        semantics="query",
        spec_sha256="4" * 64,
        ready_at_binding=True,
    )
    with pytest.raises(AgentTaskError, match="arguments do not match"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {"max_age_ms": 1000},
            tool=selected_tool,
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="active revision selection"):
        coordinator._append_execution(
            task_id,
            "other.query",
            "query",
            {},
            tool=selected_tool.model_copy(update={"tool_id": "other.query"}),
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="active revision selection"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "action",
            {},
            tool=selected_tool.model_copy(update={"semantics": "action"}),
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="stale revision"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {},
            tool=selected_tool,
            planning_binding=validated.model_copy(update={"revision_id": "revision-stale"}),
        )
    assert coordinator.get_task(task_id).active_revision.execution_records == []

    capture_calls = 0

    async def capture_before(_task_id):
        nonlocal capture_calls
        capture_calls += 1

    monkeypatch.setattr(coordinator, "_capture_before", capture_before)
    with pytest.raises(AgentTaskError, match="active revision selection"):
        asyncio.run(
            coordinator.start_action(
                task_id,
                "scene.observe",
                {},
                planning_binding=validated,
            )
        )
    assert capture_calls == 0

    class QueryClient:
        async def invoke_query_tool(self, *_args, **_kwargs):
            return {"ok": True, "data": {"status": "available"}}

    coordinator.client = QueryClient()
    from PhyAgentOS.agent.loop import AgentLoop
    from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
    from PhyAgentOS.agent.tools.registry import ToolRegistry

    loop = object.__new__(AgentLoop)
    loop._planning_dispatch = dispatch
    loop.forge_task_coordinator = coordinator
    loop._allows_pre_graph_discovery_query = lambda *_args: False
    registry = ToolRegistry()
    registry.register(ForgeToolQueryTool(coordinator.client, coordinator))
    registry.set_execution_guard(loop._planning_guard)
    result = json.loads(asyncio.run(registry.execute("forge_tool_query", {
        "task_id": task_id, "tool_id": "scene.observe", "arguments": {},
        "use_selected_arguments": True,
    })))
    assert result["ok"] is True
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-real"
    ) is None


def test_planning_node_accepts_only_one_execution_record(tmp_path):
    task_id = "task-one-execution"
    revision_id = "revision-one-execution"
    node = PlanNode(node_id="observe", obligation_id="observe", capability="scene.observe")
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    coordinator.create_task(
        task_description="observe once",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-one-execution/revision-one-execution",
    )
    binding = PlanningExecutionBinding(
        node_id="observe",
        node_digest=plan_node_digest(node),
        obligation_id="observe",
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://planning-traces/legacy/observe/one",
    )
    tool = BoundToolSpec(
        tool_id="scene.observe",
        semantics="query",
        spec_sha256="4" * 64,
        ready_at_binding=True,
    )
    coordinator._append_execution(
        task_id,
        "scene.observe",
        "query",
        {},
        tool=tool,
        planning_binding=binding,
    )
    with pytest.raises(AgentTaskError, match="already has an execution record"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {},
            tool=tool,
            planning_binding=binding,
        )


def test_prepare_selection_builds_coordinator_owned_manipulation_intent():
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
        },
    )
    payload = {
        "task_id": "task-prepare",
        "revision_id": "revision-prepare",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="manipulation.prepare",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("manipulation.prepare",),
        trusted_argument_builder="manipulation_intent_v2",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )
    arguments = {
        "observation_ref": "observation://scene-1/camera",
        "scene_revision": "scene-1",
        "frame_id": "camera",
        "calibration_ref": "artifact://calibration/camera",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "candidate_set_ref": "candidate-set://scene-1/camera",
        "candidates": [{"entity_ref": "entity://green"}],
        "destination_ref": "destination://targets/middle",
        "capability_snapshot_ref": "artifact://capabilities/current",
        "intent": {
            "goal": "place green in the middle",
            "success_criteria": ["green reaches the resolved destination"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "constraints": ["collision free"],
        },
    }

    proposal = dispatch.prepare_selection(
        node_id=node.node_id,
        tool_id=policy.tool_id,
        arguments=arguments,
        decision_reason="check readiness",
    )

    final = proposal["tool_arguments"]
    assert final["intent"]["task_id"] == graph.task_id
    assert final["intent"]["revision_id"] == graph.revision_id
    assert final["intent"]["node_id"] == node.node_id
    assert final["intent"]["node_digest"] == proposal["node_digest"]
    assert final["intent"]["motion_authorized"] is False
    assert proposal["input_binding_digest"] == tool_input_binding_digest(final)


def test_prepare_selection_rejects_model_owned_coordinator_identity():
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
        },
    )
    payload = {
        "task_id": "task-prepare",
        "revision_id": "revision-prepare",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-1"),
    )

    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments={"intent": {"task_id": "model-authored"}},
            decision_reason="invalid ownership",
        )
    except ValueError as exc:
        assert "Coordinator-owned" in str(exc)
    else:
        raise AssertionError("model-authored Coordinator identity must be rejected")


def test_prepare_selection_accepts_documented_flat_intent_fields():
    node = PlanNode(
        node_id="prepare-flat",
        obligation_id="prepare-flat",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
            "goal": "place green in the middle",
            "success_criteria": ["green reaches the resolved destination"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "constraints": ["collision free"],
        },
    )
    payload = {
        "task_id": "task-flat",
        "revision_id": "revision-flat",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-flat"),
    )
    arguments = {
        "observation_ref": "observation://scene-flat/camera",
        "scene_revision": "scene-flat",
        "frame_id": "camera",
        "calibration_ref": "artifact://calibration/camera",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "candidate_set_ref": "candidate-set://scene-flat/camera",
        "candidates": [{"entity_ref": "entity://green"}],
        "destination_ref": "destination://targets/middle",
        "capability_snapshot_ref": "artifact://capabilities/current",
        "goal": "place green in the middle",
        "success_criteria": ["green reaches the resolved destination"],
        "allowed_arms": ["left"],
        "coordination_mode": "single_arm",
        "constraints": ["collision free"],
    }
    proposal = dispatch.prepare_selection(
        node_id=node.node_id,
        tool_id="manipulation.prepare",
        arguments=arguments,
        decision_reason="check flat contract",
    )
    assert proposal["tool_arguments"]["intent"]["goal"] == "place green in the middle"
    assert proposal["tool_arguments"]["intent"]["motion_authorized"] is False

    conflicting = dict(arguments, coordination_mode="bimanual")
    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments=conflicting,
            decision_reason="reject semantic drift",
        )
    except ValueError as exc:
        assert "does not match the semantic node" in str(exc)
    else:
        raise AssertionError("conflicting flat intent must fail before Gateway invocation")


def test_prepare_selection_rejects_non_object_nested_intent_as_contract_error():
    node = PlanNode(
        node_id="prepare-invalid",
        obligation_id="prepare-invalid",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "destination_ref": "destination://targets/middle",
            "capability_snapshot_ref": "artifact://capabilities/current",
        },
    )
    payload = {
        "task_id": "task-invalid",
        "revision_id": "revision-invalid",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-invalid"),
    )
    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments={"intent": "not-an-object"},
            decision_reason="reject invalid shape",
        )
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("non-object nested intent must be rejected as a contract error")
