"""No-motion PAOS acceptance tests for LabUtopia pour/stir cycles."""

from __future__ import annotations

import time
from datetime import timezone
from pathlib import Path

import pytest
from PhyAgentOS.forge.capability_runtime import (
    CapabilityRuntimeError,
    SceneUnderstandingInferenceRegistry,
)
from pick_place_workflow.perception_binding import BindingRequest, PerceptionBindingAdapter

from isaacsim_lab.observation import IsaacCameraObservationSource
from isaacsim_lab.paos_client import (
    LabUtopiaCycleClient,
    LabUtopiaPAOSClientError,
    build_labutopia_runtime,
)
from isaacsim_lab.profile import LabUtopiaProfile
from isaacsim_lab.task_projection import LabTaskProjectionError, project_pour_task

CALLER = "paos:task-1:revision-1:record-1"


def _profile(tmp_path: Path) -> LabUtopiaProfile:
    scene = tmp_path / "lab.usd"
    config = tmp_path / "level.yaml"
    scene.write_text("usd", encoding="utf-8")
    config.write_text("name: lab", encoding="utf-8")
    return LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path),
        "config_path": str(config),
        "scene_usd_path": str(scene),
        "robot_usd_path": str(scene),
        "source_path": "/World/conical_bottle03",
        "destination_path": "/World/beaker2",
        "source_label": "试剂A",
        "destination_label": "烧杯",
        "configured_process_type": "pour",
        "supported_operations": ["pour_cycle"],
    })


def _phases():
    names = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    facts = (
        {"grasp_confirmed": True, "possession_state": "holding"},
        {"route_completed": True, "possession_state": "holding"},
        {"possession_state": "holding"},
        {"tool_reoriented_or_exited": True, "possession_state": "holding"},
        {"object_support_state": "on_support"},
        {"release_confirmed": True, "possession_state": "empty"},
        {"retreat_completed": True, "clear_of_target": True, "observation_ready": True},
    )
    events = []
    for index, (name, phase_facts) in enumerate(zip(names, facts, strict=True)):
        start = float(index)
        end = float(index + 1)
        if index >= 3:
            start += 1.0
            end += 1.0
        events.append({
            "phase": name,
            "status": "completed",
            "outcome_known": True,
            "started_at_s": start,
            "completed_at_s": end,
            "facts": phase_facts,
        })
    events[2]["started_at_s"] = 2.0
    events[2]["completed_at_s"] = 4.0
    return events


class FakeEngine:
    def __init__(self):
        self.started = []

    def cycle_capability(self, operation):
        enabled = operation in {"pour_cycle", "stir_cycle"}
        return {
            "operation": operation,
            "preparation": enabled,
            "execution": enabled,
            "feedback": enabled,
            "return": enabled,
            "dry_run": False,
            "motion_authorized": enabled,
        }

    def prepare_cycle(self, arguments):
        return {"status": "available", "motion_authorized": False,
                "arguments": dict(arguments)}

    def execute_cycle(self, operation, arguments, cancel, **context):
        self.started.append((operation, context["invocation_id"], dict(arguments)))
        assert not cancel.is_set()
        return {
            "status": "succeeded",
            "outcome_known": True,
            "world_change_started": True,
            "new_scene_revision": "lab-2",
            "artifact_refs": ["artifact://labutopia/test-cycle"],
            "entity_ref": arguments["entity_ref"],
            "destination_ref": arguments["destination_ref"],
            "return_destination_ref": arguments["return_destination_ref"],
            "possession_state": "empty",
            "object_support_state": "on_support",
            "phase_events": _phases(),
            "feedback_source_profile": {
                "frame_id": "lab_camera_front",
                "calibration_ref": "artifact://labutopia/calibration-v1",
                "container_frame_id": "container://labutopia/beaker2",
            },
            "evaluation_profile": {
                "max_sample_gap_s": 0.5,
                "alignment_tolerance_m": 0.05,
                "tilt_tolerance_rad": 0.1,
                "maximum_tilt_rad": 1.5,
            },
            "feedback_samples": [
                {
                    "timestamp_s": timestamp,
                    "feedback_valid": True,
                    "grasp_valid": True,
                    "target_container_aligned": True,
                    "alignment_error_m": 0.001,
                    "tilt_rad": 0.87,
                    "frame_id": "lab_camera_front",
                    "calibration_ref": "artifact://labutopia/calibration-v1",
                    "container_frame_id": "container://labutopia/beaker2",
                }
                for timestamp in (2.0, 2.2, 2.4, 2.6, 2.8, 3.0)
            ],
        }


class GenericProvider:
    def capture(self, request):
        return None

    def understand(self, request):
        return None

    def propose(self, request):
        return None

    def describe(self, request):
        return None

    def prepare(self, request):
        return {"status": "unavailable", "motion_authorized": False}


def _runtime(tmp_path, engine):
    profile = _profile(tmp_path)
    engine.profile = profile
    return build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=object(),
        grasp_provider=object(),
        preparation_provider=GenericProvider(),
        capability_provider=GenericProvider(),
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=True,
    )


def test_agent_task_projection_uses_profile_bound_paths_and_labels(tmp_path):
    profile = _profile(tmp_path)
    projected = project_pour_task(profile, {
        "task_type": "pour_liquid",
        "source_label": "试剂A",
        "destination_label": "烧杯",
        "parameters": {"tilt_rad": 0.87, "hold_s": 0.4},
    })
    assert projected["source_path"] == "/World/conical_bottle03"
    assert projected["destination_path"] == "/World/beaker2"
    assert projected["paos_input"]["entity_ref"] == "entity://conical_bottle03"
    assert projected["paos_input"]["destination_ref"] == "destination://beaker2"

    with pytest.raises(LabTaskProjectionError, match="source label"):
        project_pour_task(profile, {
            "task_type": "pour_liquid", "source_label": "试剂B", "destination_label": "烧杯",
        })


def test_paos_discovers_two_cycles_and_executes_one_task_owned_pour(tmp_path):
    engine = FakeEngine()
    bundle = _runtime(tmp_path, engine)
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "object.pour_cycle" in tools
        assert "tool.stir_cycle" in tools
        assert "manipulation.cycle" not in tools
        assert "manipulation.execute_subtask" not in tools
        assert not {"object.acquire", "object.place", "object.pour", "tool.stir"} & tools

        projected = project_pour_task(bundle.engine.profile, {
            "task_type": "pour_liquid", "source_label": "试剂A", "destination_label": "烧杯",
            "parameters": {"tilt_rad": 0.87, "hold_s": 0.4},
        })
        prepared = bundle.runtime.invoke_query(
            "cycle_preparation", "prepare", projected["paos_input"]
        )
        assert prepared["status"] == "available"
        assert prepared["motion_authorized"] is False
        invocation = bundle.runtime.start_action(
            "object.pour_cycle", prepared["arguments"], caller_id=CALLER
        )["invocation_id"]
        result = None
        for _ in range(50):
            result = bundle.runtime.invocation_result(invocation)
            if result["status"] != "pending":
                break
            time.sleep(0.005)
        assert result["status"] == "succeeded"
        assert result["result"]["operation_completed"] is True
        assert result["result"]["process_completed"] is True
        assert result["result"]["return_completed"] is True
        assert [item[0] for item in engine.started] == ["pour_cycle"]
        assert len(engine.started) == 1
    finally:
        bundle.client.close()


def test_invalid_task_caller_cannot_start_labutopia_cycle(tmp_path):
    engine = FakeEngine()
    bundle = _runtime(tmp_path, engine)
    try:
        args = project_pour_task(bundle.engine.profile, {
            "task_type": "pour_liquid", "source_label": "试剂A", "destination_label": "烧杯",
        })["paos_input"]
        prepared = bundle.runtime.invoke_query("cycle_preparation", "prepare", args)
        with pytest.raises(CapabilityRuntimeError):
            bundle.runtime.start_action(
                "object.pour_cycle", prepared["arguments"], caller_id="not-a-paos-task"
            )
        assert engine.started == []
    finally:
        bundle.client.close()


def test_labutopia_registers_subtask_only_with_generic_perception_chain(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    provider = GenericProvider()
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )
    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=provider,
        grasp_provider=provider,
        preparation_provider=provider,
        capability_provider=provider,
        observation_source=provider,
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
        subtask_context_resolver=lambda _caller: None,
    )
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "manipulation.execute_subtask" in tools
        assert bundle.perception_adapter is not None
        assert bundle.perception_adapter.query_invoker is bundle.runtime
    finally:
        bundle.client.close()


def test_labutopia_does_not_register_subtask_with_unimplemented_query_providers(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )
    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=object(),
        grasp_provider=object(),
        preparation_provider=object(),
        capability_provider=GenericProvider(),
        observation_source=object(),
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
        subtask_context_resolver=lambda _caller: {},
    )
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "manipulation.execute_subtask" not in tools
        assert bundle.perception_adapter is None
    finally:
        bundle.client.close()


def test_labutopia_does_not_register_subtask_without_coordinator_context(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    provider = GenericProvider()
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )
    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=provider,
        grasp_provider=provider,
        preparation_provider=provider,
        capability_provider=provider,
        observation_source=provider,
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
    )
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "manipulation.execute_subtask" not in tools
        assert bundle.perception_adapter is not None
    finally:
        bundle.client.close()


def test_labutopia_observation_query_uses_injected_source_not_action_client(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile

    class Camera:
        def get_rgb(self):
            return [[[(10, 20, 30)]]]

    class ArtifactWriter:
        def write(self, sensor_ref, kind, value, *, captured_at):
            assert value
            assert captured_at.tzinfo is timezone.utc
            return {
                "ref": "artifact://observations/observed-scene-1/rgb",
                "media_type": "application/x-numpy",
            }

    observation_source = IsaacCameraObservationSource(
        {"camera/front": Camera()},
        lambda _sensor_ref: {
            "scene_revision": "observed-scene-1",
            "frame_id": "lab-camera-front",
            "calibration_ref": "artifact://calibration/lab-camera-front-v1",
        },
        ArtifactWriter(),
    )
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )
    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=object(),
        grasp_provider=object(),
        preparation_provider=GenericProvider(),
        capability_provider=GenericProvider(),
        observation_source=observation_source,
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
    )
    try:
        result = bundle.runtime.invoke_query(
            "scene_observation", "observe",
            {"sensor_ref": "camera/front", "max_age_ms": 1000},
        )
        assert result["status"] == "available"
        assert result["scene_revision"] == "observed-scene-1"
        assert result["frame"]["frame_id"] == "lab-camera-front"
        assert engine.started == []
    finally:
        bundle.client.close()


def test_labutopia_runtime_composes_shared_artifact_understanding(tmp_path):
    artifact_root = tmp_path / "observation-artifacts"
    artifact_root.mkdir()
    (artifact_root / "front.png").write_bytes(b"camera-bytes")
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    seen = []
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )

    class Provider:
        def capture(self, _request):
            return None

        def propose(self, _request):
            return None

        def describe(self, _request):
            return None

        def prepare(self, _request):
            return None

    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=None,
        understanding_inference=lambda request: seen.append(request) or {"entities": []},
        observation_artifact_root=artifact_root,
        grasp_provider=Provider(),
        preparation_provider=Provider(),
        capability_provider=Provider(),
        observation_source=Provider(),
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
        subtask_context_resolver=lambda _caller: None,
    )
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "manipulation.execute_subtask" in tools
        assert bundle.perception_adapter is not None
        result = bundle.runtime.invoke_query(
            "scene_understanding",
            "understand",
            {
                "observation_ref": "observation://scene-1/camera-front",
                "scene_revision": "scene-1",
                "frame_id": "camera-front",
                "calibration_ref": "artifact://labutopia/front.png",
                "freshness_ms": 10,
                "max_age_ms": 100,
                "artifacts": ["artifact://labutopia/front.png"],
            },
        )
        assert result["status"] == "available"
        assert seen[0]["resolved_artifacts"][0]["data"] == b"camera-bytes"
        assert seen[0]["resolved_artifacts"][0]["media_type"] == "image/png"
    finally:
        bundle.client.close()


def test_labutopia_runtime_composes_registry_selected_understanding(tmp_path):
    artifact_root = tmp_path / "observation-artifacts"
    artifact_root.mkdir()
    (artifact_root / "front.png").write_bytes(b"camera-bytes")
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    seen = []
    adapter = PerceptionBindingAdapter(
        lambda _tool_id, _arguments: {},
        BindingRequest(("camera/front",), "reagent_a", "beaker", 1000),
    )

    class Provider:
        def capture(self, _request):
            return None

        def propose(self, _request):
            return None

        def describe(self, _request):
            return None

        def prepare(self, _request):
            return None

    class Factory:
        inference_id = "fixture"

        def create(self, *, configuration):
            seen.append(("configuration", configuration))
            return lambda request: seen.append(("inference", request)) or {"entities": []}

    registry = SceneUnderstandingInferenceRegistry()
    registry.register(Factory())
    bundle = build_labutopia_runtime(
        profile=profile,
        engine=engine,
        understanding_provider=None,
        understanding_inference_registry=registry,
        understanding_inference_id="fixture",
        understanding_inference_configuration={"deployment": "test"},
        observation_artifact_root=artifact_root,
        grasp_provider=Provider(),
        preparation_provider=Provider(),
        capability_provider=Provider(),
        observation_source=Provider(),
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
        subtask_context_resolver=lambda _caller: None,
    )
    try:
        result = bundle.runtime.invoke_query(
            "scene_understanding",
            "understand",
            {
                "observation_ref": "observation://scene-1/camera-front",
                "scene_revision": "scene-1",
                "frame_id": "camera-front",
                "calibration_ref": "artifact://labutopia/front.png",
                "freshness_ms": 10,
                "max_age_ms": 100,
                "artifacts": ["artifact://labutopia/front.png"],
            },
        )
        assert result["status"] == "available"
        assert seen[0] == ("configuration", {"deployment": "test"})
        assert seen[1][1]["resolved_artifacts"][0]["data"] == b"camera-bytes"
    finally:
        bundle.client.close()


@pytest.mark.parametrize(
    "resolver,inference",
    [(object(), None)],
)
def test_labutopia_runtime_rejects_incomplete_understanding_composition(
    tmp_path, resolver, inference
):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile

    class Provider:
        def propose(self, _request):
            return None

        def describe(self, _request):
            return None

        def prepare(self, _request):
            return None

    with pytest.raises(ValueError, match="composition is required"):
        build_labutopia_runtime(
            profile=profile,
            engine=engine,
            understanding_provider=None,
            understanding_artifact_resolver=resolver,
            understanding_inference=inference,
            grasp_provider=Provider(),
            preparation_provider=Provider(),
            capability_provider=Provider(),
            resolve_preparation=lambda operation, arguments: dict(arguments),
            tool_context_provider=lambda _: {"ready": True},
            allow_live=False,
            observation_artifact_root=tmp_path / "observation-artifacts",
        )


def test_labutopia_runtime_requires_explicit_root_for_local_inference(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile

    class Provider:
        def propose(self, _request):
            return None

        def describe(self, _request):
            return None

        def prepare(self, _request):
            return None

    with pytest.raises(ValueError, match="observation_artifact_root is required"):
        build_labutopia_runtime(
            profile=profile,
            engine=engine,
            understanding_provider=None,
            understanding_inference=lambda _request: {"entities": []},
            grasp_provider=Provider(),
            preparation_provider=Provider(),
            capability_provider=Provider(),
            resolve_preparation=lambda operation, arguments: dict(arguments),
            tool_context_provider=lambda _: {"ready": True},
        )


def test_labutopia_runtime_passes_explicit_root_to_default_worker_backend(tmp_path):
    profile = _profile(tmp_path)
    artifact_root = tmp_path / "deployment-observations"
    provider = GenericProvider()
    bundle = build_labutopia_runtime(
        profile=profile,
        understanding_provider=provider,
        grasp_provider=provider,
        preparation_provider=provider,
        capability_provider=provider,
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        observation_artifact_root=artifact_root,
    )
    try:
        assert bundle.engine.backend.observation_artifact_root == artifact_root.resolve()
    finally:
        bundle.client.close()


def test_client_defaults_to_no_motion_and_reports_dry_run_capability(tmp_path):
    engine = FakeEngine()
    client = LabUtopiaCycleClient(engine)
    try:
        capability = client.cycle_capability("pour_cycle")
        assert capability["dry_run"] is True
        assert capability["execution"] is False
        with pytest.raises(LabUtopiaPAOSClientError, match="live LabUtopia execution is disabled"):
            client.start("pour_cycle", "invocation://pour/1", "paos:task-1", {})
    finally:
        client.close()
