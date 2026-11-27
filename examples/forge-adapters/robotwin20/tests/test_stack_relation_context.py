"""Public dispatch and durable Coordinator evidence through real no-motion preparation."""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from jsonschema import validate
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import NodeContextProvider
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec
from PhyAgentOS.forge.capability_runtime.grasp_proposal import (
    GRASP_TOOL_SPEC,
    GraspProposalEndpoint,
)
from PhyAgentOS.forge.capability_runtime.manipulation_capabilities import (
    CAPABILITY_TOOL_SPEC,
    CapabilitySnapshotEndpoint,
)
from PhyAgentOS.forge.manipulation import MANIPULATION_INTENT_SEMANTIC_KEYS
from PhyAgentOS.forge.task import AgentTaskCoordinator, ToolExecutionRecord
from PhyAgentOS.planning import AdmissionContext, plan_node_digest, project_tool_spec
from PhyAgentOS.verification.contracts import TaskVerificationContract
from pick_place_workflow.agent_planning import compose_executable_relation_plan
from pick_place_workflow.grounding import BIND_TOOL_SPEC
from pick_place_workflow.relation_execution import (
    RELATION_ESTABLISH_TOOL_SPEC,
    RelationEstablishActionEndpoint,
)
from pick_place_workflow.relation_target import (
    RELATION_TARGET_TOOL_SPEC,
    RelationTargetQueryEndpoint,
)
from robotwin_blocks_ranking_adapter import StackBlocksThreeTaskAdapter
from test_arm_candidates import _intent
from test_observed_relation_target import observed_scene
from test_stack_relation_preparation import composed

from robotwin20_adapter.route_evidence import _artifact_path
from robotwin20_adapter.stack_relation_inputs import build_stack_relation_preparation_inputs
from robotwin20_adapter.stack_relation_preparation import (
    build_stack_relation_execution_provider_factory,
)

SPECS = (
    BIND_TOOL_SPEC,
    GRASP_TOOL_SPEC,
    CAPABILITY_TOOL_SPEC,
    RELATION_TARGET_TOOL_SPEC,
    RELATION_ESTABLISH_TOOL_SPEC,
)


def chain(tmp_path, *, observed=False, moving_execution=2):
    seed = _intent()
    if observed:
        seed = seed.model_copy(update={"node_id": "place_base" if moving_execution == 1 else "place_middle"})
    identity = {
        key: getattr(seed, key) for key in ("scene_revision", "observation_ref", "calibration_ref")
    }
    semantic = {
        key: value
        for key, value in seed.model_dump(mode="json").items()
        if key in MANIPULATION_INTENT_SEMANTIC_KEYS
    }
    goals = {
            "schema_version": "paos-task-goals/v1",
            "motion_authorized": False,
            "goals": [
                {
                    "subtask_id": seed.node_id,
                    "execution_entity_ref": seed.entity_ref,
                    "goal_relation": "on",
                    "relation_target_ref": "surface://table",
                    "produced_evidence": ["support-established"],
                }
            ],
        }
    projection = None
    observed_state = None
    available = (seed.observation_ref, "tool:understanding")
    if observed:
        observed_state = observed_scene(tmp_path, identity=identity, moving_execution=moving_execution)
        goals = StackBlocksThreeTaskAdapter().goal_facts(None, seed=0)
        goals["goal_ref"] = "artifact://task/goal"
        projection = observed_state.provider.project_relation_goal(
            goals, subtask_id=seed.node_id, binding_ref=observed_state.bound["binding_ref"],
            identity=observed_state.request)
        available = (*available, *projection["evidence_refs"])
        # This segment starts after a successful predecessor fixture; no
        # current-segment Query or future grasp is pre-completed.
        selected_goal = next(goal for goal in goals["goals"] if goal["subtask_id"] == seed.node_id)
        for goal in goals["goals"]:
            if goal["subtask_id"] in selected_goal["depends_on"]:
                available = (*available, *goal["produced_evidence"])
    graph = compose_executable_relation_plan(
        seed.task_id, seed.revision_id, goals,
        subtask_id=seed.node_id,
        **identity,
        observation_frame_id=seed.observation_frame_id,
        understanding_evidence_ref="tool:understanding",
        semantic_intent=semantic,
        freshness_ms=0,
        max_age_ms=1000,
        available_evidence=available,
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
        relation_projection=projection,
    ).graph
    expected_intent = seed.model_copy(update={"node_digest": plan_node_digest(graph.nodes[-1])})
    request, inputs, deployment, seen = composed(
        tmp_path, intent_override=expected_intent,
        grounding_override=observed_state.grounding if observed else None)
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    coordinator.create_task(
        task_description="prepare one relation",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/relation",
    )
    provenance = ["artifact://blocks/points/red"]
    understanding = {
        "status": "available",
        **identity,
        "frame": {"frame_id": seed.observation_frame_id, "unit": "m"},
        "entities": [{"entity_ref": seed.entity_ref, "category": "block", "confidence": 0.95}],
        "spatial_envelopes": [
            {
                "entity_ref": seed.entity_ref,
                "frame_id": seed.observation_frame_id,
                "unit": "m",
                "min_xyz_m": [0.1, 0.1, 0.1],
                "max_xyz_m": [0.2, 0.2, 0.2],
                "confidence": 0.95,
                "provenance": provenance,
            }
        ],
    }
    if observed:
        understanding = observed_state.understanding
        provenance = understanding["spatial_envelopes"][moving_execution - 1]["provenance"]

    def discovery(task):
        task.active_revision.discovery_evidence_refs = available
        task.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="understanding",
                revision_id=seed.revision_id,
                tool_id="scene.understand",
                semantics="query",
                caller_id="discovery",
                arguments={
                    **identity,
                    "frame_id": seed.observation_frame_id,
                    "freshness_ms": 0,
                    "max_age_ms": 1000,
                },
                status="succeeded",
                response={"ok": True, "data": understanding},
                evidence_refs=["tool:understanding"],
            )
        )

    coordinator.store.update(seed.task_id, discovery, event_type="fixture_observed_understanding")
    policies = tuple(project_tool_spec(spec) for spec in SPECS)
    bound = {
        spec["tool_id"]: BoundToolSpec(
            tool_id=spec["tool_id"],
            semantics=spec["semantics"],
            spec_sha256=policy.spec_digest,
            ready_at_binding=True,
            planning_policy=policy,
            input_schema=spec["input_schema"],
        )
        for spec, policy in zip(SPECS, policies)
    }
    context_provider = NodeContextProvider(
        coordinator.get_task,
        settlement_loader=coordinator.effective_node_settlements,
        execution_record_loader=coordinator.effective_planning_execution_records,
    )

    def admission(_task):
        return AdmissionContext(
            scene_revision=seed.scene_revision,
            evidence_refs=frozenset(available),
            settlements={
                item.node_id: item.status
                for item in coordinator.effective_node_settlements(seed.task_id)
            },
        )

    dispatch = AgentComposedDispatch(
        graph,
        policies,
        admission(seed.task_id),
        context_provider=admission,
        node_context_provider=context_provider,
        input_schemas={spec["tool_id"]: spec["input_schema"] for spec in SPECS},
    )
    selector = ForgePlanSelectTool(coordinator, lambda: dispatch)
    selected_nodes = []

    def select(node, **kwargs):
        visible = {item["node_id"]: item for item in dispatch.describe()["ready_nodes"]}
        assert node.node_id in visible
        assert node.capability in visible[node.node_id]["candidate_tool_ids"]
        output = json.loads(
            asyncio.run(
                selector.execute(
                    task_id=seed.task_id,
                    node_id=node.node_id,
                    tool_id=node.capability,
                    decision_reason="use current persisted evidence",
                    **kwargs,
                )
            )
        )
        assert output["ok"], output
        pending = coordinator.pending_planning_selection(
            seed.task_id, node.node_id, scene_revision=seed.scene_revision
        )
        args = pending["arguments"]
        validate(args, bound[node.capability].input_schema)
        record_id, caller = coordinator._append_execution(
            seed.task_id,
            node.capability,
            bound[node.capability].semantics,
            args,
            tool=bound[node.capability],
            planning_binding=output["data"]["planning_binding"],
        )
        selected_nodes.append(node.capability)
        return record_id, caller, args

    candidate = {
        "candidate_ref": "candidate://red-block/1",
        "entity_ref": seed.entity_ref,
        "grasp_frame": {
            "frame_id": seed.observation_frame_id,
            "unit": "m",
            "position_m": [0.1, 0.1, 0.1],
            "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
        "approach_direction": {
            "frame_id": seed.observation_frame_id,
            "unit": "unitless",
            "vector": [0.0, 0.0, 1.0],
        },
        "score": 0.9,
        "confidence": 0.9,
        "provenance": provenance,
        "qualification": "proposed",
    }
    results = {}
    records = {}
    artifact_path = tmp_path / "relation/support.json"
    artifact_path.parent.mkdir(exist_ok=True)
    for node in graph.nodes[:-1]:
        kwargs = {"arguments": dict(node.input_bindings)}
        if node.capability == "scene.bind":
            kwargs = {
                "arguments": {"entity_refs": node.input_bindings["entity_refs"]},
                "projection_sources": {"understanding": {"record_id": "understanding"}},
            }
        elif node.capability == "grasp.propose":
            kwargs = {"projection_source": {"record_id": "understanding"}}
        record_id, caller, args = select(node, **kwargs)
        if node.capability == "scene.bind":
            result = {
                "status": "available",
                "motion_authorized": False,
                **identity,
                "binding_ref": inputs["binding_ref"],
                "frame_id": "world",
                "unit": "m",
                "observation_frame_id": seed.observation_frame_id,
                "entities": [
                    {"entity_ref": seed.entity_ref, "execution_entity_ref": seed.entity_ref}
                ],
            }
            if observed:
                result = deployment.grounding.bind(args)
                validate(result, BIND_TOOL_SPEC["output_schema"])
        elif node.capability == "grasp.propose":
            result = GraspProposalEndpoint(
                SimpleNamespace(
                    propose=lambda _: {
                        "candidates": [candidate],
                        "ambiguities": [],
                        "funnel": {
                            name: 1
                            for name in ("decoded", "canonicalized", "deduplicated", "retained")
                        },
                    }
                )
            ).invoke(args)
            validate(result, GRASP_TOOL_SPEC["output_schema"])
        elif node.capability == "manipulation.capabilities":
            capability = json.loads((tmp_path / "scene/capability.json").read_text())
            result = CapabilitySnapshotEndpoint(
                SimpleNamespace(describe=lambda _: capability)
            ).invoke(args)
        elif observed:
            result = RelationTargetQueryEndpoint(observed_state.provider).invoke(args)
            validate(result, RELATION_TARGET_TOOL_SPEC["output_schema"])
            assert result["status"] == "available", result
            selected = result["candidates"][0]
            request["candidate_ref"] = selected["candidate_ref"]
            artifact_path = _artifact_path(tmp_path, selected["evidence_refs"][0])
        else:
            artifact_path.write_text(
                json.dumps(
                    {
                        "schema_version": "paos-robotwin20-relation-target-evidence/v1",
                        "task_name": "stack_blocks_three",
                        "query": args,
                        "geometry_source": "simulator_actor_geometry",
                        "support_world_top_m": 0.5,
                        "motion_authorized": False,
                    }
                )
            )
            relation_candidate = {
                "candidate_ref": request["candidate_ref"],
                "destination_ref": request["relation_binding"]["destination_ref"],
                "world_T_object_target": request["relation_binding"]["world_T_object_target"],
                "evidence_refs": ["artifact://relation/support"],
            }
            result = RelationTargetQueryEndpoint(
                SimpleNamespace(
                    propose=lambda _: {
                        **{
                            key: value
                            for key, value in args.items()
                            if key not in {"freshness_ms", "max_age_ms"}
                        },
                        "status": "available",
                        "candidate_set_ref": "relation-target-set://scene/current",
                        "candidates": [relation_candidate],
                        "motion_authorized": False,
                    }
                )
            ).invoke(args)
            validate(result, RELATION_TARGET_TOOL_SPEC["output_schema"])
        assert result["status"] == "available", result
        coordinator._finish_execution(
            seed.task_id, record_id, status="succeeded", response={"ok": True, "data": result}
        )
        records[node.capability] = record_id
        results[node.capability] = result
    record_id, caller, action = select(
        graph.nodes[-1], arguments={"candidate_ref": request["candidate_ref"]}
    )
    provider = build_stack_relation_execution_provider_factory(
        prepare_inputs=build_stack_relation_preparation_inputs(
            tmp_path, task_name="stack_blocks_three"
        )
    )(deployment.preparation_provider.client, deployment)
    endpoint = RelationEstablishActionEndpoint(provider, coordinator.resolve_relation_context)
    # Capture the production endpoint's internal request without replacing preparation.
    captured = []
    original_admit = provider.admit

    def admit(value, **kwargs):
        captured.append(deepcopy(value))
        return original_admit(value, **kwargs)

    provider.admit = admit
    admission = endpoint.admit_for_caller(action, caller_id=caller).start(
        "invocation-1", "attempt-1"
    )
    assert admission.terminal_result["error"]["code"] == "stack_relation_motion_unqualified"
    assert not seen
    return SimpleNamespace(
        coordinator=coordinator,
        dispatch=dispatch,
        context_provider=context_provider,
        provider=provider,
        endpoint=endpoint,
        request=captured[0],
        action=action,
        caller=caller,
        deployment=deployment,
        seen=seen,
        records=records,
        results=results,
        graph=graph,
        selected_nodes=selected_nodes,
        artifact_path=artifact_path,
        task_id=seed.task_id,
        observed_state=observed_state,
        goals=goals,
    )


def test_public_dispatch_durable_queries_endpoint_and_real_preparation(tmp_path):
    state = chain(tmp_path)
    assert state.selected_nodes == [spec["tool_id"] for spec in SPECS]
    assert "candidates" not in state.action and "candidate_set_ref" not in state.action
    assert "coordinator_context" not in RELATION_ESTABLISH_TOOL_SPEC["input_schema"]["properties"]
    before = deepcopy(state.request)
    starts = []
    state.deployment.preparation_provider.client.start = lambda *args, **kwargs: starts.append(args)
    route = state.provider.prepare_route(state.request, state.task_id)
    assert state.request == before
    assert route["task_id"] == state.task_id
    assert route["capability_snapshot_ref"] == "artifact://scene/capability"
    assert route["candidate_ref"] == "candidate://red-block/1"
    assert route["assignment"]["motion_authorized"] is False
    assert state.seen[0]["target_geometry_source"] == "simulator_actor_geometry"
    assert state.seen[0]["geometry_source"] == "observation"
    assert (
        state.seen[0]["objects"][0]["world_T_object_target"]
        == state.request["relation_binding"]["world_T_object_target"]
    )
    assert starts == []


@pytest.mark.parametrize("moving_execution", [1, 2])
def test_observed_dispatch_prepares_visual_identity_and_full_collision_scene(tmp_path, moving_execution):
    state = chain(tmp_path, observed=True, moving_execution=moving_execution)
    before = deepcopy(state.goals)
    starts = []
    state.deployment.preparation_provider.client.start = lambda *args, **kwargs: starts.append(args)
    route = state.provider.prepare_route(state.request, state.task_id)
    assert state.goals == before
    assert route["entity_ref"] == "entity://red-block"
    assert route["assignment"]["motion_authorized"] is False
    facts = state.seen[0]
    assert facts["geometry_source"] == facts["target_geometry_source"] == "observation"
    assert {obj["entity_ref"] for obj in facts["objects"]} == set(state.observed_state.visual.values())
    context = state.request["coordinator_context"]["predecessor_queries"]
    bound = context["scene.bind"]["result"]
    assert context["relation.target"]["arguments"]["binding_ref"] == bound["binding_ref"]
    mapping = next(item for item in bound["entities"] if item["entity_ref"] == route["entity_ref"])
    assert mapping["execution_entity_ref"] == f"entity://stack-block-{moving_execution}"
    assert mapping["execution_entity_ref"] != route["entity_ref"]
    assert state.provider.motion_supported() is False
    assert starts == []


@pytest.mark.parametrize("change", ["binding", "mapping", "pose", "calibration", "clouds", "depth"])
def test_observed_artifact_drift_rejects_before_preparation(tmp_path, change):
    state = chain(tmp_path, observed=True)
    evidence = json.loads(state.artifact_path.read_text())
    if change == "binding":
        evidence["binding_ref"] = "artifact://binding/wrong"
    elif change == "mapping":
        evidence["execution_mappings"][0]["execution_entity_ref"] = "entity://other"
    elif change == "pose":
        evidence["world_T_object_target"][3] += 0.1
    elif change == "calibration":
        evidence["calibration_ref"] = "artifact://calibration/wrong"
    elif change == "clouds":
        evidence["cloud_refs"] = []
    else:
        evidence.pop("depth_ref")
    state.artifact_path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="observed relation evidence"):
        state.provider.prepare_route(state.request, state.task_id)
    assert not state.seen and not state.deployment.grounding.targets


@pytest.mark.parametrize("change", ["missing", "query", "source", "task", "motion"])
def test_artifact_failure_prevents_target_publication_and_preparation(tmp_path, change):
    state = chain(tmp_path)
    evidence = json.loads(state.artifact_path.read_text())
    if change == "missing":
        state.artifact_path.unlink()
    else:
        if change == "query":
            evidence["query"]["frame_id"] = "wrong"
        if change == "source":
            evidence.pop("geometry_source")
        if change == "task":
            evidence["task_name"] = "other"
        if change == "motion":
            evidence["motion_authorized"] = True
        state.artifact_path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="artifact"):
        state.provider.prepare_route(state.request, state.task_id)
    assert not state.seen and not state.deployment.grounding.targets


@pytest.mark.parametrize("change", ["candidate", "pose", "identity", "execution_identity", "frame"])
def test_persisted_query_binding_mismatch_is_rejected(tmp_path, change):
    state = chain(tmp_path)
    request = state.request
    if change == "candidate":
        request["candidate_ref"] = "relation-target://other/1"
    if change == "pose":
        request["relation_binding"]["world_T_object_target"][3] += 0.1
    queries = request["coordinator_context"]["predecessor_queries"]
    if change == "identity":
        queries["grasp.propose"]["arguments"]["scene_revision"] = "other"
    if change == "execution_identity":
        queries["scene.bind"]["result"]["entities"][0]["execution_entity_ref"] = (
            "entity://different"
        )
    if change == "frame":
        queries["scene.bind"]["result"]["observation_frame_id"] = "world"
    with pytest.raises(ValueError):
        state.provider.prepare_route(request, state.task_id)
    assert not state.seen and not state.deployment.grounding.targets


@pytest.mark.parametrize(
    "change",
    [
        "cross_revision",
        "not_direct",
        "duplicate",
        "failed",
        "unsettled",
        "stale",
        "caller",
        "intent",
    ],
)
def test_coordinator_rejects_invalid_direct_predecessor_or_caller(tmp_path, change):
    state = chain(tmp_path)

    def mutate(task):
        revision = task.active_revision
        record = next(
            item
            for item in revision.execution_records
            if item.record_id == state.records["grasp.propose"]
        )
        if change == "cross_revision":
            record.revision_id = "old-revision"
        if change == "not_direct":
            record.node_id = "unrelated"
        if change == "duplicate":
            revision.execution_records.append(record.model_copy(update={"record_id": "duplicate"}))
        if change == "failed":
            record.status = "failed"
        if change == "unsettled":
            revision.node_settlements = [
                item for item in revision.node_settlements if item.node_id != record.node_id
            ]
        if change == "stale":
            record.response["data"]["scene_revision"] = "old-scene"
        if change == "intent":
            action = revision.execution_records[-1]
            action.arguments["intent"]["goal"] = "changed"

    if change == "cross_revision":
        # The authoritative store already prevents cross-revision records.
        with pytest.raises(RuntimeError, match="authoritative record schema"):
            state.coordinator.store.update(
                state.task_id, mutate, event_type="fixture_invalid_evidence"
            )
        return
    state.coordinator.store.update(state.task_id, mutate, event_type="fixture_invalid_evidence")
    caller = (
        state.caller.replace(":revision-1:", ":old-revision:")
        if change == "caller"
        else state.caller
    )
    with pytest.raises((ValueError, RuntimeError)):
        state.coordinator.resolve_relation_context(caller)
    assert not state.seen and not state.deployment.grounding.targets


def test_current_scene_change_rejects_mutually_stale_node_and_grasp(tmp_path):
    state = chain(tmp_path)
    from PhyAgentOS.forge.manipulation_context import relation_manipulation_intent

    context = state.context_provider.build(
        state.task_id,
        state.graph.nodes[-1].node_id,
        scene_revision=state.graph.nodes[-1].input_bindings["scene_revision"],
    )
    with pytest.raises(ValueError, match="current context"):
        relation_manipulation_intent(
            state.graph,
            state.graph.nodes[-1],
            context.model_copy(update={"scene_revision": "new-scene"}),
        )
