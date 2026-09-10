from __future__ import annotations

from datetime import datetime, timezone

import pytest
from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.agent.planning_loop import (
    AgentLoopNodeExecutor,
    NodeContextProvider,
    PlanningLoopAdapter,
)
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.capability_runtime import (
    GraspProposalSnapshot,
    PreparationSnapshot,
    UnderstandingSnapshot,
)
from PhyAgentOS.forge.manipulation import (
    ArmCapability,
    CapabilitySnapshot,
    ResourceMode,
    capability_snapshot_digest,
)
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.forge.tool_client import ForgeToolClient
from PhyAgentOS.planning import AdmissionContext, PlanningExecutionBinding, plan_node_digest
from PhyAgentOS.verification.contracts import (
    CriterionVerdict,
    TaskVerificationContract,
    VerificationAttempt,
    VerificationVerdict,
)
from pick_place_workflow.multi_object_agent import MultiObjectAgentRunner

from robotwin20_adapter.persistent_deployment import (
    PersistentDeployment,
    build_persistent_runtime_bundle,
)


class PersistentFixtureClient:
    """Controlled worker seam with the same revision/possession semantics as the engine."""

    def __init__(self) -> None:
        self.revision = 0
        self.scene_revision = "runtime-0"
        self.holding: str | None = None
        self.starts: list[dict] = []

    def query(self, operation, arguments):
        if operation == "observe":
            return {
                "captured_at": datetime.now(timezone.utc),
                "scene_revision": self.scene_revision,
                "frame_id": "camera_head",
                "calibration_ref": "artifact://calibration/head",
                "artifacts": [
                    {
                        "ref": f"artifact://observations/{self.scene_revision}/rgb",
                        "kind": "rgb",
                        "media_type": "image/png",
                    }
                ],
            }
        if operation == "snapshot":
            return {
                "scene_revision": self.scene_revision,
                "holding_state": "holding" if self.holding else "empty",
            }
        raise AssertionError(f"unexpected query: {operation}")

    def start(self, phase, invocation_id, owner, arguments):
        assert owner == "paos:task-persistent-multi"
        assert arguments["scene_revision"] == self.scene_revision
        self.starts.append(
            {
                "phase": phase,
                "invocation_id": invocation_id,
                "scene_revision": self.scene_revision,
                "entity_ref": arguments["entity_ref"],
            }
        )
        return PersistentFixtureDriver(self, phase, arguments["entity_ref"])


class PersistentFixtureDriver:
    def __init__(self, client, phase, entity_ref):
        self.client = client
        self.phase = phase
        self.entity_ref = entity_ref
        self.pending = True

    def poll(self):
        if self.pending:
            self.pending = False
            return None
        if self.phase == "acquire":
            assert self.client.holding is None
            self.client.holding = self.entity_ref
        else:
            assert self.client.holding == self.entity_ref
            self.client.holding = None
        self.client.revision += 1
        self.client.scene_revision = f"runtime-{self.client.revision}"
        return {
            "status": "succeeded",
            "outcome_known": True,
            "world_change_started": True,
            "new_scene_revision": self.client.scene_revision,
            "artifact_refs": [
                f"artifact://persistent/{self.client.scene_revision}/{self.phase}"
            ],
        }

    def cancel(self):
        raise AssertionError("success-path fixture must not cancel")

    def stop(self):
        self.cancel()


class PreparedFixture:
    def __init__(self, client):
        self.client = client

    def __call__(self, phase, arguments):
        result = {
            **arguments,
            "assignment": {
                "task_id": "task-persistent-multi",
                "assignment_ref": arguments["assignment_ref"],
            },
        }
        if phase == "place":
            result["scene_revision"] = self.client.scene_revision
        return result

    def prepare(self, request):
        candidate = request["candidates"][0]
        return PreparationSnapshot(
            prepared_candidates=(
                {
                    "candidate_ref": candidate["candidate_ref"],
                    "entity_ref": candidate["entity_ref"],
                    "checks": {
                        "kinematic": "pass",
                        "collision": "pass",
                        "workspace": "pass",
                    },
                    "evidence": [
                        f"artifact://preparation/{request['scene_revision']}/readiness"
                    ],
                    "qualification": "prepared",
                },
            )
        )


class UnderstandingFixture:
    def understand(self, request):
        artifact_ref = request["artifacts"][0]
        return UnderstandingSnapshot(
            entities=tuple(
                {
                    "entity_ref": f"entity://{name}",
                    "category": "block",
                    "confidence": 1.0,
                    "provenance": [artifact_ref],
                }
                for name in ("green", "red")
            ),
            spatial_envelopes=tuple(
                {
                    "entity_ref": f"entity://{name}",
                    "frame_id": request["frame_id"],
                    "unit": "m",
                    "min_xyz_m": [0.0, 0.0, 0.0],
                    "max_xyz_m": [0.1, 0.1, 0.1],
                    "confidence": 1.0,
                    "provenance": [artifact_ref],
                }
                for name in ("green", "red")
            ),
        )


class GraspFixture:
    def propose(self, request):
        target = request["targets"][0]
        entity_ref = target["entity_ref"]
        name = entity_ref.removeprefix("entity://")
        return GraspProposalSnapshot(
            candidates=(
                {
                    "candidate_ref": f"candidate://{name}/0",
                    "entity_ref": entity_ref,
                    "grasp_frame": {
                        "frame_id": request["frame_id"],
                        "unit": "m",
                        "position_m": [0.05, 0.05, 0.05],
                        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    },
                    "approach_direction": {
                        "frame_id": request["frame_id"],
                        "unit": "unitless",
                        "vector": [0.0, 0.0, -1.0],
                    },
                    "score": 1.0,
                    "confidence": 1.0,
                    "provenance": list(target["spatial_envelope"]["provenance"]),
                    "qualification": "proposed",
                },
            ),
            funnel={
                "decoded": 1,
                "canonicalized": 1,
                "deduplicated": 1,
                "retained": 1,
            },
        )


class CapabilityFixture:
    def __init__(self, client):
        self.client = client

    def describe(self, request):
        payload = {
            "snapshot_ref": f"artifact://capabilities/{request['scene_revision']}",
            "snapshot_digest": "0" * 64,
            "scene_revision": request["scene_revision"],
            "observation_ref": request["observation_ref"],
            "calibration_ref": request["calibration_ref"],
            "embodiment_id": "fixture-arm",
            "topology": "single_arm",
            "profile_digest": "1" * 64,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "arms": (
                ArmCapability(
                    arm_id="arm",
                    base_frame="base",
                    tool_frame="tool",
                    planner_profile_ref="artifact://profiles/planner",
                    workspace_ref="artifact://profiles/workspace",
                    joint_limits_ref="artifact://profiles/joint-limits",
                    gripper_identity="gripper",
                    supported_modes=(ResourceMode.SINGLE_RESOURCE,),
                ),
            ),
            "motion_authorized": False,
        }
        payload["snapshot_digest"] = capability_snapshot_digest(payload)
        return CapabilitySnapshot.model_validate(payload)


class AggregateVerifier:
    def __init__(self):
        self.final_scene_revision = None
        self.calls = 0

    async def verify_agent_task(self, task, *, events, lessons, source, mode):
        del events, lessons, mode
        self.calls += 1
        facts = [response_facts(record.response) for record in task.execution_records]
        self.final_scene_revision = next(
            item["scene_revision"]
            for item in reversed(facts)
            if item.get("status") == "available" and "scene_revision" in item
        )
        verdict = VerificationVerdict(
            verdict="success",
            criteria=[
                CriterionVerdict(
                    criterion="both selected objects are placed", status="satisfied"
                )
            ],
            reason="aggregate persistent execution facts satisfy the task",
            lesson="none",
        )
        return (
            verdict,
            {"verdict": "success"},
            VerificationAttempt(
                attempt_id="verification-persistent-multi",
                source=source,
                verdict="success",
            ),
        )


def _entity(name):
    return {
        "entity_ref": f"entity://{name}",
        "benchmark_object_ref": f"block-{name}",
        "destination_ref": f"destination://slot/{name}",
        "observation_ref": "observation://runtime-0/camera_head",
        "scene_revision": "runtime-0",
        "frame_id": "camera_head",
        "calibration_ref": "artifact://calibration/head",
        "geometry_artifact_ref": f"artifact://geometry/{name}",
        "category": "block",
    }


def _action_arguments(entity_ref, scene_revision, *, acquire_ref=None):
    name = entity_ref.removeprefix("entity://")
    arguments = {
        "observation_ref": f"observation://{scene_revision}/camera_head",
        "scene_revision": scene_revision,
        "frame_id": "camera_head",
        "calibration_ref": "artifact://calibration/head",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "candidate_set_ref": f"candidate-set://{scene_revision}/camera_head",
        "preparation_ref": f"preparation://{scene_revision}/camera_head",
        "candidate_ref": f"candidate://{name}/0",
        "entity_ref": entity_ref,
        "capability_snapshot_ref": f"artifact://capabilities/{scene_revision}",
        "assignment_ref": f"artifact://assignments/{scene_revision}/{name}",
    }
    if acquire_ref is not None:
        arguments.update(
            acquire_invocation_ref=acquire_ref,
            destination_ref=f"destination://slot/{name}",
        )
    return arguments


@pytest.mark.asyncio
async def test_two_object_agent_loop_uses_one_persistent_runtime_and_final_verifier(tmp_path):
    worker = PersistentFixtureClient()
    prepared = PreparedFixture(worker)
    deployment = PersistentDeployment(
        preparation_provider=prepared,
        capability_provider=CapabilityFixture(worker),
        prepared_routes=prepared,
    )
    bundle = build_persistent_runtime_bundle(
        deployment=deployment,
        client=worker,
        understanding_provider=UnderstandingFixture(),
        grasp_provider=GraspFixture(),
        tool_context_provider=lambda _tool_id: {
            "ready": True,
            "max_concurrency": 1,
            "motion_authorized": False,
        },
    )
    verifier = AggregateVerifier()
    async with ForgeToolClient("http://persistent-runtime", transport=bundle.transport) as client:
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
            scene_revision_provider=lambda _task_id: worker.scene_revision,
            planning_mode="baseline",
        )
        task = await runner.create_task(
            task_description="place the green and red blocks",
            entities=[_entity("green"), _entity("red")],
            verification=TaskVerificationContract(
                mode="enforce",
                goal="place both selected blocks",
                success_criteria=["both selected objects are placed"],
            ),
            task_id="task-persistent-multi",
            revision_id="revision-persistent-multi",
        )
        node_scenes = []
        object_scenes = {}

        class Agent:
            async def run_node_turn(self, *, task_id, revision_id, node_id, **_kwargs):
                current_task = coordinator.get_task(task_id)
                node = next(
                    item
                    for item in current_task.active_revision.plan_graph.nodes
                    if item.node_id == node_id
                )
                node_scenes.append((node_id, worker.scene_revision))
                binding = PlanningExecutionBinding(
                    node_id=node_id,
                    node_digest=plan_node_digest(node),
                    obligation_id=node.obligation_id,
                    input_binding_digest="a" * 64,
                    decision_trace_ref=f"artifact://trace/{node_id}",
                )
                if node_id == "verify":
                    await coordinator.invoke_query(
                        task_id,
                        "scene.observe",
                        {"sensor_ref": "camera/head", "max_age_ms": 1000},
                        planning_binding=binding,
                    )
                    return
                entity_ref = node.input_bindings["entity_ref"]
                if node.capability == "scene.observe":
                    object_scenes[entity_ref] = worker.scene_revision
                    await coordinator.invoke_query(
                        task_id,
                        node.capability,
                        {"sensor_ref": "camera/head", "max_age_ms": 1000},
                        planning_binding=binding,
                    )
                    return
                source_scene = object_scenes[entity_ref]
                observation_ref = f"observation://{source_scene}/camera_head"
                artifact_ref = f"artifact://observations/{source_scene}/rgb"
                common = {
                    "observation_ref": observation_ref,
                    "scene_revision": source_scene,
                    "frame_id": "camera_head",
                    "calibration_ref": "artifact://calibration/head",
                    "freshness_ms": 0,
                    "max_age_ms": 1000,
                }
                if node.capability == "manipulation.capabilities":
                    arguments = {
                        key: common[key]
                        for key in (
                            "scene_revision",
                            "observation_ref",
                            "calibration_ref",
                        )
                    }
                elif node.capability == "scene.understand":
                    arguments = {**common, "artifacts": [artifact_ref]}
                elif node.capability == "grasp.propose":
                    arguments = {
                        **common,
                        "targets": [
                            {
                                "entity_ref": entity_ref,
                                "category": "block",
                                "confidence": 1.0,
                                "spatial_envelope": {
                                    "frame_id": "camera_head",
                                    "unit": "m",
                                    "min_xyz_m": [0.0, 0.0, 0.0],
                                    "max_xyz_m": [0.1, 0.1, 0.1],
                                    "confidence": 1.0,
                                    "provenance": [artifact_ref],
                                },
                            }
                        ],
                    }
                elif node.capability == "manipulation.prepare":
                    arguments = {
                        **common,
                        "candidate_set_ref": (
                            f"candidate-set://{source_scene}/camera_head"
                        ),
                        "candidates": [
                            {
                                "candidate_ref": (
                                    f"candidate://{entity_ref.removeprefix('entity://')}/0"
                                ),
                                "entity_ref": entity_ref,
                                "grasp_frame": {
                                    "frame_id": "camera_head",
                                    "unit": "m",
                                    "position_m": [0.05, 0.05, 0.05],
                                    "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
                                },
                                "approach_direction": {
                                    "frame_id": "camera_head",
                                    "unit": "unitless",
                                    "vector": [0.0, 0.0, -1.0],
                                },
                                "score": 1.0,
                                "confidence": 1.0,
                                "provenance": [artifact_ref],
                                "qualification": "proposed",
                            }
                        ],
                    }
                elif node.capability == "object.acquire":
                    await coordinator.start_action(
                        task_id,
                        node.capability,
                        _action_arguments(entity_ref, source_scene),
                        planning_binding=binding,
                    )
                    return
                elif node.capability == "object.place":
                    acquire_id = next(
                        record.invocation_id
                        for record in reversed(
                            coordinator.get_task(task_id).execution_records
                        )
                        if record.tool_id == "object.acquire"
                        and response_facts(record.response).get("entity_ref") == entity_ref
                    )
                    await coordinator.start_action(
                        task_id,
                        node.capability,
                        _action_arguments(
                            entity_ref,
                            source_scene,
                            acquire_ref=acquire_id,
                        ),
                        planning_binding=binding,
                    )
                    return
                else:
                    raise AssertionError(f"unexpected Tool: {node.capability}")
                await coordinator.invoke_query(
                    task_id,
                    node.capability,
                    arguments,
                    planning_binding=binding,
                )

        def admission(task_id):
            evidence = {
                ref
                for record in coordinator.get_task(task_id).execution_records
                for ref in record.evidence_refs
            }
            return AdmissionContext(
                scene_revision=worker.scene_revision,
                evidence_refs=frozenset(evidence),
            )

        result = await PlanningLoopAdapter(
            coordinator,
            context_provider=NodeContextProvider(coordinator.get_task),
            node_executor=AgentLoopNodeExecutor(Agent(), coordinator),
            admission_context_provider=admission,
        ).run(task.task_id, scene_revision="runtime-0")

    assert result.status == "succeeded"
    assert dict(node_scenes)["relocate_1.observe"] == "runtime-0"
    assert dict(node_scenes)["relocate_2.observe"] == "runtime-2"
    assert dict(node_scenes)["verify"] == "runtime-4"
    assert [(item["phase"], item["scene_revision"]) for item in worker.starts] == [
        ("acquire", "runtime-0"),
        ("place", "runtime-1"),
        ("acquire", "runtime-2"),
        ("place", "runtime-3"),
    ]
    assert worker.holding is None
    assert verifier.calls == 1
    assert verifier.final_scene_revision == "runtime-4"
    records = coordinator.get_task(task.task_id).execution_records
    assert [record.tool_id for record in records] == [
        "scene.observe",
        "manipulation.capabilities",
        "scene.understand",
        "grasp.propose",
        "manipulation.prepare",
        "object.acquire",
        "object.place",
        "scene.observe",
        "manipulation.capabilities",
        "scene.understand",
        "grasp.propose",
        "manipulation.prepare",
        "object.acquire",
        "object.place",
        "scene.observe",
    ]
    assert all(record.terminal and record.status == "succeeded" for record in records)
    action_records = [record for record in records if record.semantics == "action"]
    assert len({record.invocation_id for record in action_records}) == 4
    assert all(record.attempt_id for record in action_records)
