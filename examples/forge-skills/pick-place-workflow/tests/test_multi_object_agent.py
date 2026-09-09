from __future__ import annotations

import pytest
from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.agent.planning_loop import (
    AgentLoopNodeExecutor,
    NodeContextProvider,
    PlanningLoopAdapter,
)
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.capability_runtime import (
    ActionAdmission,
    CapabilityRuntime,
    CapabilityRuntimeTransport,
)
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError
from PhyAgentOS.forge.tool_client import ForgeToolClient
from PhyAgentOS.planning import (
    AdmissionContext,
    NodeSettlement,
    PlanningExecutionBinding,
    ToolResultEnvelope,
    plan_node_digest,
)
from PhyAgentOS.verification.contracts import (
    CriterionVerdict,
    TaskVerificationContract,
    VerificationAttempt,
    VerificationVerdict,
)

from pick_place_workflow.multi_object_agent import (
    MultiObjectAgentError,
    MultiObjectAgentRunner,
    SceneObjectBinding,
    bind_scene_objects,
    bind_understood_scene_objects,
)


def entity(name: str, *, destination: str | None = None, scene: str = "scene://s0") -> dict:
    return {
        "entity_ref": f"entity://{name}",
        "benchmark_object_ref": f"block-{name}-1",
        "destination_ref": destination or f"region://{name}",
        "observation_ref": "artifact://observation/s0",
        "scene_revision": scene,
        "frame_id": "camera_front",
        "calibration_ref": "artifact://calibration/front",
        "geometry_artifact_ref": f"artifact://geometry/{name}",
        "category": "block",
    }


def understood_scene(*names: str):
    understanding = {
        "status": "available",
        "observation_ref": "observation://s0/camera_front",
        "scene_revision": "scene://s0",
        "frame": {"frame_id": "camera_front", "unit": "m"},
        "calibration_ref": "artifact://calibration/front",
        "entities": [
            {
                "entity_ref": f"entity://{name}",
                "category": "block",
                "confidence": 0.95,
                "provenance": ["artifact://observation/s0/rgb"],
            }
            for name in names
        ],
        "ambiguities": [],
        "derived_artifacts": [
            {
                "artifact_ref": f"artifact://geometry/{name}",
                "entity_ref": f"entity://{name}",
                "observation_ref": "observation://s0/camera_front",
                "scene_revision": "scene://s0",
                "frame_id": "camera_front",
                "calibration_ref": "artifact://calibration/front",
                "provenance": ["artifact://observation/s0/depth"],
            }
            for name in names
        ],
    }
    measured = [
        {
            "entity_ref": f"entity://{name}",
            "benchmark_object_ref": f"block-{name}-1",
            "destination_ref": f"destination://slot-{name}",
            "observation_ref": "observation://s0/camera_front",
            "scene_revision": "scene://s0",
            "frame_id": "camera_front",
            "calibration_ref": "artifact://calibration/front",
            "geometry_artifact_ref": f"artifact://geometry/{name}",
            "category": "block",
        }
        for name in names
    ]
    return understanding, measured


class DeterministicTaskVerifier:
    """Record the aggregate supplied to the final Verifier and return a fixed verdict."""

    def __init__(self, verdict: str = "success") -> None:
        self.verdict_name = verdict
        self.received_tasks = []
        self.received_events = []

    async def verify_agent_task(self, task, *, events, lessons, source, mode):
        del lessons
        self.received_tasks.append(task.model_copy(deep=True))
        self.received_events.append(list(events))
        criterion_status = {
            "success": "satisfied",
            "failure": "unsatisfied",
            "inconclusive": "unknown",
        }[self.verdict_name]
        verdict = VerificationVerdict(
            verdict=self.verdict_name,
            criteria=[CriterionVerdict(criterion="both objects are placed", status=criterion_status)],
            reason=f"deterministic {self.verdict_name} verdict",
            lesson="none",
        )
        return verdict, {"verdict": self.verdict_name}, VerificationAttempt(
            attempt_id=f"verification-{len(self.received_tasks)}",
            source=source,
            mode=mode,
            verdict=self.verdict_name,
        )


def test_scene_binding_accepts_optional_capability_and_assignment_evidence():
    bound = SceneObjectBinding.model_validate({
        **entity("green"),
        "capability_snapshot_ref": "artifact://capabilities/s0",
        "assignment_ref": "artifact://assignments/s0/green",
    })
    assert bound.capability_snapshot_ref == "artifact://capabilities/s0"
    assert bound.assignment_ref == "artifact://assignments/s0/green"
    with pytest.raises(ValueError, match="artifact://"):
        SceneObjectBinding.model_validate({**entity("red"), "assignment_ref": "assignment://bad"})


def test_bind_scene_objects_excludes_surface_and_requires_unique_bindings():
    values = bind_scene_objects([
        entity("green"),
        {**entity("table"), "category": "desktop_surface"},
    ])
    assert [item.entity_ref for item in values] == ["entity://green"]
    with pytest.raises(MultiObjectAgentError, match="destination_ref"):
        bind_scene_objects([entity("a"), entity("b", destination="region://a")])


def test_bind_scene_objects_rejects_mixed_scene_revision():
    with pytest.raises(MultiObjectAgentError, match="scene revision"):
        bind_scene_objects([entity("a", scene="scene://s0"), entity("b", scene="scene://s1")])


def test_bind_understood_scene_objects_can_select_one_semantic_entity():
    understanding, measured = understood_scene("green", "red")
    bound = bind_understood_scene_objects(
        understanding, measured, entity_refs=["entity://red"],
    )
    assert [item.entity_ref for item in bound] == ["entity://red"]
    assert bound[0].destination_ref == "destination://slot-red"
    assert bound[0].required_evidence == (
        "artifact://geometry/red", "artifact://observation/s0/depth",
    )


def test_bind_understood_scene_objects_joins_all_unique_measured_objects():
    understanding, measured = understood_scene("green", "red")
    bound = bind_understood_scene_objects(understanding, measured)
    assert [item.entity_ref for item in bound] == ["entity://green", "entity://red"]
    assert {item.benchmark_object_ref for item in bound} == {"block-green-1", "block-red-1"}


def test_bind_understood_scene_objects_rejects_duplicate_geometry_artifacts():
    understanding, measured = understood_scene("green", "red")
    understanding["derived_artifacts"].append(dict(understanding["derived_artifacts"][0]))
    with pytest.raises(MultiObjectAgentError, match="geometry artifact identities"):
        bind_understood_scene_objects(understanding, measured)


@pytest.mark.parametrize(
    ("change", "message"),
    [("ambiguity", "ambiguities"), ("scene", "drift"), ("geometry", "geometry evidence")],
)
def test_bind_understood_scene_objects_rejects_untrusted_join(change, message):
    understanding, measured = understood_scene("green")
    if change == "ambiguity":
        understanding["ambiguities"] = [{"code": "ambiguous", "entity_refs": ["entity://green"]}]
    elif change == "scene":
        measured[0]["scene_revision"] = "scene://stale"
    else:
        measured[0]["geometry_artifact_ref"] = "artifact://geometry/other"
    with pytest.raises(MultiObjectAgentError, match=message):
        bind_understood_scene_objects(understanding, measured)


@pytest.mark.asyncio
async def test_runner_creates_plan_from_understanding_and_measured_scene(tmp_path):
    understanding, measured = understood_scene("green", "red")
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
    )
    task = await runner.create_task_from_scene_understanding(
        task_description="place the red and green blocks",
        understanding=understanding,
        measured_objects=measured,
        verification=TaskVerificationContract(mode="off"),
        task_id="task-understood-scene",
        revision_id="revision-understood-scene",
        entity_refs=["entity://red", "entity://green"],
    )
    graph = task.active_revision.plan_graph
    assert graph is not None
    assert {
        node.input_bindings["entity_ref"]
        for node in graph.nodes
        if "entity_ref" in node.input_bindings
    } == {"entity://red", "entity://green"}


@pytest.mark.asyncio
async def test_runner_creates_one_task_with_all_object_obligations(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode="baseline",
    )
    task = await runner.create_task(
        task_description="sort two blocks",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(mode="off", success_criteria=["both blocks placed"]),
        task_id="task-multi-1",
        revision_id="revision-multi-1",
    )
    graph = task.active_revision.plan_graph
    assert graph is not None
    assert task.task_id == "task-multi-1"
    assert {node.obligation_id for node in graph.nodes if node.node_id != "verify"} == {
        "relocate_1", "relocate_2"
    }
    assert set(graph.nodes[-1].dependencies) == {"relocate_1.place", "relocate_2.place"}
    bindings = {node.node_id: node.input_bindings for node in graph.nodes}
    assert bindings["relocate_1.observe"] == {
        "entity_ref": "entity://green",
        "destination_ref": "region://green",
        "benchmark_object_ref": "block-green-1",
        "observation_ref": "artifact://observation/s0",
        "scene_revision": "scene://s0",
        "frame_id": "camera_front",
        "calibration_ref": "artifact://calibration/front",
        "geometry_artifact_ref": "artifact://geometry/green",
    }
    assert bindings["relocate_2.place"]["geometry_artifact_ref"] == "artifact://geometry/red"
    assert len(task.revisions) == 1


@pytest.mark.asyncio
async def test_runner_semantic_mode_does_not_force_tool_queue(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode="agent_composed",
    )
    task = await runner.create_task(
        task_description="sort one block",
        entities=[SceneObjectBinding.model_validate(entity("green"))],
        verification=TaskVerificationContract(mode="off"),
        task_id="task-semantic-1",
        revision_id="revision-semantic-1",
    )
    nodes = {node.node_id: node for node in task.active_revision.plan_graph.nodes}
    assert list(nodes) == ["relocate_1", "verify"]
    assert nodes["relocate_1"].input_bindings["scene_revision"] == "scene://s0"


@pytest.mark.asyncio
@pytest.mark.parametrize("planning_mode", ["baseline", "agent_composed"])
async def test_runner_persists_optional_execution_evidence_in_plan_nodes(tmp_path, planning_mode):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode=planning_mode,
    )
    task = await runner.create_task(
        task_description="evidence-bound block",
        entities=[{
            **entity("green"),
            "capability_snapshot_ref": "artifact://capabilities/s0",
            "assignment_ref": "artifact://assignments/s0/green",
        }],
        verification=TaskVerificationContract(mode="off"),
        task_id=f"task-evidence-{planning_mode}",
        revision_id=f"revision-evidence-{planning_mode}",
    )
    nodes = [node for node in task.active_revision.plan_graph.nodes if node.node_id != "verify"]
    assert nodes
    assert all(node.input_bindings["capability_snapshot_ref"] == "artifact://capabilities/s0" for node in nodes)
    assert all(node.input_bindings["assignment_ref"] == "artifact://assignments/s0/green" for node in nodes)


@pytest.mark.asyncio
async def test_runner_rejects_stale_scene_before_agent_loop(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    class AgentLoop:
        def build_long_horizon_controller(self):
            raise AssertionError("stale scene must be rejected before controller creation")

    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=AgentLoop(),
        scene_revision_provider=lambda _task_id: "scene://new",
    )
    with pytest.raises(MultiObjectAgentError, match="stale"):
        await runner.run(
            task_description="stale scene",
            entities=[entity("green")],
            verification=TaskVerificationContract(mode="off"),
            task_id="task-stale-1",
            revision_id="revision-stale-1",
        )
    with pytest.raises(AgentTaskError, match="not found"):
        coordinator.get_task("task-stale-1")


@pytest.mark.asyncio
async def test_two_object_dry_run_propagates_scene_revision_to_later_object(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
    )
    task = await runner.create_task(
        task_description="place two blocks sequentially",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(mode="off"),
        task_id="task-revision-propagation",
        revision_id="revision-revision-propagation",
    )
    current_scene = {"value": "scene://s0"}
    contexts: list[tuple[str, str]] = []

    def admission(_task_id: str) -> AdmissionContext:
        return AdmissionContext(scene_revision=current_scene["value"])

    def execute(context):
        contexts.append((context.node_id, context.scene_revision))
        changed = context.node_id.endswith(".place")
        next_scene = None
        evidence = ()
        if changed:
            next_scene = "scene://s2" if current_scene["value"] == "scene://s0" else "scene://s3"
            current_scene["value"] = next_scene
            entity_ref = context.input_bindings["entity_ref"]
            evidence = (f"placed:{entity_ref}",)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id=context.capability,
            status="succeeded",
            world_changed=changed,
            new_scene_revision=next_scene,
            evidence_refs=evidence,
        )

    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=NodeContextProvider(coordinator.get_task),
        node_executor=execute,
        admission_context_provider=admission,
    )
    result = await adapter.run(task.task_id, scene_revision="scene://s0")
    assert result.status == "completed"
    assert contexts[-1] == ("verify", "scene://s3")
    assert next(scene for node, scene in contexts if node == "relocate_2.observe") == "scene://s2"
    assert [node for node, _ in contexts if node.endswith(".place")] == [
        "relocate_1.place", "relocate_2.place"
    ]


@pytest.mark.asyncio
async def test_two_object_action_loop_reconciles_scene_revisions_and_final_verify(tmp_path):
    class Query:
        def invoke(self, arguments):
            return {
                "status": "available",
                "scene_revision": arguments["scene_revision"],
                "evidence_refs": [f"observed:{arguments.get('entity_ref', 'task')}"],
            }

    class Action:
        def __init__(self, tool_id):
            self.tool_id = tool_id

        def admit(self, arguments):
            if self.tool_id == "object.place":
                next_scene = "scene://s2" if arguments["scene_revision"] == "scene://s0" else "scene://s3"
                return ActionAdmission(
                    pending_polls=1,
                    terminal_result={
                        "status": "succeeded",
                        "world_changed": True,
                        "new_scene_revision": next_scene,
                        "evidence_refs": [f"placed:{arguments['entity_ref']}"],
                        "capability_outcome_summary": {
                            "world_change_started": True,
                            "outcome_known": True,
                        },
                    },
                )
            return ActionAdmission(
                pending_polls=1,
                terminal_result={
                    "status": "succeeded",
                    "world_changed": False,
                    "evidence_refs": [f"acquired:{arguments['entity_ref']}"],
                    "capability_outcome_summary": {
                        "world_change_started": True,
                        "outcome_known": True,
                    },
                },
            )

    def register(runtime, tool_id, endpoint_id, operation, semantics, endpoint):
        runtime.register_tool(
            {
                "tool_id": tool_id,
                "endpoint_id": endpoint_id,
                "operation": operation,
                "semantics": semantics,
                "description": f"Provider-neutral {tool_id} endpoint.",
            },
            endpoint,
        )

    runtime = CapabilityRuntime()
    for tool_id, endpoint_id, operation in (
        ("scene.observe", "scene", "observe"),
        ("manipulation.capabilities", "manipulation", "capabilities"),
        ("scene.understand", "scene", "understand"),
        ("grasp.propose", "grasp", "propose"),
        ("manipulation.prepare", "manipulation", "prepare"),
        ("task.verify", "task", "verify"),
    ):
        register(runtime, tool_id, endpoint_id, operation, "query", Query())
    register(runtime, "object.acquire", "object", "acquire", "action", Action("object.acquire"))
    register(runtime, "object.place", "object", "place", "action", Action("object.place"))

    transport = CapabilityRuntimeTransport(runtime)
    verifier = DeterministicTaskVerifier()
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        coordinator = AgentTaskCoordinator(
            workspace=tmp_path,
            config=ForgeConfig(),
            client=client,
            verifier=verifier,
        )
        async def no_capture(_task_id):
            return None

        coordinator._capture_before = no_capture
        coordinator._capture_after = no_capture
        runner = MultiObjectAgentRunner(
            coordinator=coordinator,
            agent_loop=object(),
            scene_revision_provider=lambda _task_id: "scene://s0",
            planning_mode="baseline",
        )
        task = await runner.create_task(
            task_description="place two blocks sequentially",
            entities=[entity("green"), entity("red")],
            verification=TaskVerificationContract(
                mode="enforce",
                goal="place both blocks in their assigned regions",
                success_criteria=["both objects are placed"],
            ),
            task_id="task-runtime-multi",
            revision_id="revision-runtime-multi",
        )
        contexts = []

        class Agent:
            async def run_node_turn(self, *, task_id, revision_id, node_id, **_kwargs):
                current_task = coordinator.get_task(task_id)
                node = next(item for item in current_task.active_revision.plan_graph.nodes if item.node_id == node_id)
                current_scene = "scene://s0"
                for record in current_task.execution_records:
                    facts = response_facts(record.response)
                    if isinstance(facts.get("new_scene_revision"), str):
                        current_scene = facts["new_scene_revision"]
                contexts.append((node_id, current_scene))
                binding = PlanningExecutionBinding(
                    node_id=node_id,
                    node_digest=plan_node_digest(node),
                    obligation_id=node.obligation_id,
                    input_binding_digest="a" * 64,
                    decision_trace_ref=f"artifact://trace/{node_id}",
                )
                arguments = {
                    "entity_ref": node.input_bindings.get("entity_ref", "entity://task"),
                    "scene_revision": current_scene,
                }
                if node.capability in {"object.acquire", "object.place"}:
                    await coordinator.start_action(
                        task_id,
                        node.capability,
                        arguments,
                        planning_binding=binding,
                    )
                else:
                    await coordinator.invoke_query(
                        task_id,
                        node.capability,
                        arguments,
                        planning_binding=binding,
                    )

        def admission(task_id):
            scene = "scene://s0"
            evidence = set()
            for record in coordinator.get_task(task_id).execution_records:
                facts = response_facts(record.response)
                if isinstance(facts.get("new_scene_revision"), str):
                    scene = facts["new_scene_revision"]
                evidence.update(item for item in record.evidence_refs if isinstance(item, str))
            return AdmissionContext(scene_revision=scene, evidence_refs=frozenset(evidence))

        executor = AgentLoopNodeExecutor(Agent(), coordinator)
        result = await PlanningLoopAdapter(
            coordinator,
            context_provider=NodeContextProvider(coordinator.get_task),
            node_executor=executor,
            admission_context_provider=admission,
        ).run(task.task_id, scene_revision="scene://s0")

    assert result.status == "succeeded"
    assert dict(contexts)["relocate_1.place"] == "scene://s0"
    assert dict(contexts)["relocate_2.observe"] == "scene://s2"
    assert dict(contexts)["relocate_2.place"] == "scene://s2"
    assert dict(contexts)["verify"] == "scene://s3"
    records = coordinator.get_task(task.task_id).execution_records
    assert all(record.terminal and record.status == "succeeded" for record in records)
    action_invocations = [
        record.invocation_id for record in records if record.semantics == "action"
    ]
    assert len(action_invocations) == 4
    assert all(isinstance(invocation_id, str) for invocation_id in action_invocations)
    finalized = coordinator.get_task(task.task_id)
    assert finalized.status.value == "succeeded"
    assert finalized.verdict is not None
    assert finalized.verdict.verdict == "success"
    assert finalized.verification_attempts
    assert len(verifier.received_tasks) == 1
    verified = verifier.received_tasks[0]
    verified_graph = verified.active_revision.plan_graph
    assert verified_graph is not None
    assert {
        node.input_bindings["entity_ref"]
        for node in verified_graph.nodes
        if "entity_ref" in node.input_bindings
    } == {"entity://green", "entity://red"}
    assert any(
        response_facts(record.response).get("new_scene_revision") == "scene://s3"
        for record in verified.execution_records
    )
    assert all(record.evidence_refs for record in verified.execution_records)


@pytest.mark.asyncio
async def test_finalize_rejects_partially_completed_multi_object_plan(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
    )
    task = await runner.create_task(
        task_description="place two blocks sequentially",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(mode="off"),
        task_id="task-partial-finalize",
        revision_id="revision-partial-finalize",
    )
    graph = task.active_revision.plan_graph
    assert graph is not None
    for node in graph.nodes:
        if node.obligation_id == "relocate_1":
            coordinator.record_node_settlement(NodeSettlement(
                task_id=task.task_id,
                revision_id=task.active_revision_id,
                node_id=node.node_id,
                status="completed",
            ))

    with pytest.raises(AgentTaskError, match="incomplete node settlements"):
        await coordinator.finalize_task(task.task_id)

    current = coordinator.get_task(task.task_id)
    assert current.status.value == "executing"
    assert current.verdict is None


@pytest.mark.asyncio
async def test_multi_object_verifier_rejection_does_not_report_success(tmp_path):
    class QueryClient:
        async def invoke_query_tool(self, tool_id, arguments, *, caller_id, timeout_ms):
            del caller_id, timeout_ms
            return {
                "data": {
                    "status": "succeeded",
                    "tool_id": tool_id,
                    "scene_revision": arguments.get("scene_revision", "scene://s3"),
                    "evidence_refs": [f"observed:{arguments.get('entity_ref', 'task')}"],
                }
            }

    verifier = DeterministicTaskVerifier("failure")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=QueryClient(),
        verifier=verifier,
    )
    async def no_capture(_task_id):
        return None

    coordinator._capture_after = no_capture
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode="baseline",
    )
    task = await runner.create_task(
        task_description="place two blocks sequentially",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(
            mode="enforce",
            goal="place both blocks in their assigned regions",
            success_criteria=["both objects are placed"],
        ),
        task_id="task-verifier-rejection",
        revision_id="revision-verifier-rejection",
    )
    graph = task.active_revision.plan_graph
    assert graph is not None
    for node in graph.nodes:
        binding = PlanningExecutionBinding(
            node_id=node.node_id,
            node_digest=plan_node_digest(node),
            obligation_id=node.obligation_id,
            input_binding_digest="a" * 64,
            decision_trace_ref=f"artifact://trace/{node.node_id}",
        )
        await coordinator.invoke_query(
            task.task_id,
            node.capability,
            {
                "entity_ref": node.input_bindings.get("entity_ref", "entity://task"),
                "scene_revision": "scene://s3",
            },
            planning_binding=binding,
        )
        coordinator.record_node_settlement(NodeSettlement(
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            node_id=node.node_id,
            status="completed",
            scene_revision="scene://s3",
            source_tool_id=node.capability,
            outcome_known=True,
        ))

    finalized = await coordinator.finalize_task(task.task_id)

    assert finalized.status.value == "failed"
    assert finalized.verdict is not None
    assert finalized.verdict.verdict == "failure"
    assert finalized.verification_attempts
    assert all(record.terminal and record.status == "succeeded" for record in finalized.execution_records)
