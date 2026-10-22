"""No-motion PAOS acceptance tests for LabUtopia pour/stir cycles."""

from __future__ import annotations

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
    LabUtopiaCycleProvider,
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


def _binding(profile, *, entity_ref="entity://observed-reagent-a", destination_ref="destination://observed-beaker"):
    return {
        "entity_ref": entity_ref,
        "semantic_label": "试剂A",
        "category": "reagent_bottle",
        "destination_ref": destination_ref,
        "destination_label": "烧杯",
        "observation_ref": "observation://observed-scene/camera-front",
        "scene_revision": "observed-scene",
        "frame_id": profile.frame_id,
        "calibration_ref": profile.calibration_ref,
        "freshness_ms": 5,
        "max_age_ms": profile.max_age_ms,
        "binding_ref": "artifact://bindings/observed-scene/reagent-a",
    }


def _resolved_target(binding):
    frame = binding["frame_id"]
    pose = {
        "frame_id": frame, "unit": "m", "position_m": [0.2, 0.1, 0.8],
        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    return {
        "candidate_ref": "candidate://observed-reagent-a/grasp-1",
        "entity_ref": binding["entity_ref"],
        "destination_ref": binding["destination_ref"],
        "scene_revision": binding["scene_revision"],
        "frame_id": frame,
        "calibration_ref": binding["calibration_ref"],
        "control_frame_id": frame,
        "world_from_control": {
            "parent_frame_id": "world", "child_frame_id": frame,
            "translation_m": [0.0, 0.0, 0.0],
            "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
        "entity_prim_path": "/World/measured_source",
        "destination_prim_path": "/World/measured_destination",
        "object_pose": pose,
        "grasp_frame": pose,
        "approach_direction": {"frame_id": frame, "unit": "unitless", "vector": [0.0, 0.0, -1.0]},
        "destination_pose": pose,
        "return_pose": pose,
        "process_frame": {"frame_id": frame, "origin_m": [0.2, 0.1, 0.8], "axis": [0.0, 0.0, 1.0]},
    }


def test_labutopia_target_resolver_is_replaceable_and_binding_owned(tmp_path):
    profile = _profile(tmp_path)
    binding = _binding(profile)

    class Engine:
        def __init__(self, profile):
            self.profile = profile
            self.requests = []

        def prepare_cycle(self, request):
            self.requests.append(dict(request))
            return {"status": "available", "arguments": dict(request)}

    class ResolverA:
        def resolve(self, observed, request):
            assert observed == binding
            assert request["operation"] == "pour_cycle"
            return _resolved_target(observed)

    class ResolverB:
        def resolve(self, observed, request):
            target = _resolved_target(observed)
            target["entity_prim_path"] = "/World/another_provider_object"
            return target

    engine = Engine(profile)
    request = {
        "operation": "pour_cycle", "entity_ref": binding["entity_ref"],
        "destination_ref": binding["destination_ref"],
        "scene_revision": binding["scene_revision"], "frame_id": binding["frame_id"],
        "calibration_ref": binding["calibration_ref"], "binding": binding,
    }
    result = LabUtopiaCycleProvider(engine, target_resolver=ResolverA()).prepare_cycle(request)
    assert result["status"] == "available"
    assert engine.requests[0]["manipulation_target"]["entity_prim_path"] == "/World/measured_source"

    engine.requests.clear()
    replaced = LabUtopiaCycleProvider(engine, target_resolver=ResolverB()).prepare_cycle(request)
    assert replaced["status"] == "available"
    assert engine.requests[0]["manipulation_target"]["entity_prim_path"] == "/World/another_provider_object"

    engine.requests.clear()
    mismatched = _resolved_target(binding)
    mismatched["entity_ref"] = "entity://unrelated"

    class MismatchedResolver:
        def resolve(self, _observed, _request):
            return mismatched

    result = LabUtopiaCycleProvider(engine, target_resolver=MismatchedResolver()).prepare_cycle(request)
    assert result["status"] == "invalid"
    assert engine.requests == []

    unavailable = LabUtopiaCycleProvider(engine).prepare_cycle(request)
    assert unavailable["status"] == "unavailable"
    assert engine.requests == []

    stale_request = dict(request)
    stale_request["binding"] = {**binding, "freshness_ms": 1001}
    stale = LabUtopiaCycleProvider(engine, target_resolver=ResolverA()).prepare_cycle(stale_request)
    assert stale["status"] == "invalid"
    assert engine.requests == []


def test_labutopia_standard_preparation_consumes_binding_and_returns_provider_route(tmp_path):
    profile = _profile(tmp_path)
    binding = _binding(profile)

    class Engine:
        def __init__(self, profile):
            self.profile = profile
            self.requests = []

        def prepare_manipulation(self, request):
            self.requests.append(dict(request))
            candidate = request["candidates"][0]
            return {
                "status": "available",
                "prepared_candidates": [{
                    "candidate_ref": candidate["candidate_ref"],
                    "entity_ref": candidate["entity_ref"],
                    "qualification": "prepared",
                    "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                    "evidence": ["artifact://readiness/lab-route"],
                }],
                "assignments": [],
                "destination_ref": request["destination_ref"],
                "route_arguments": {
                    "entity_ref": request["entity_ref"],
                    "candidate_ref": candidate["candidate_ref"],
                    "preparation_ref": "preparation://observed-scene/lab-camera-front",
                    "scene_revision": request["scene_revision"],
                    "destination_ref": request["destination_ref"],
                },
            }

    class Resolver:
        def resolve(self, observed, request):
            assert observed == binding
            return _resolved_target(observed)

    engine = Engine(profile)
    provider = LabUtopiaCycleProvider(engine, target_resolver=Resolver())
    request = {
        "entity_ref": binding["entity_ref"],
        "destination_ref": binding["destination_ref"],
        "observation_ref": binding["observation_ref"],
        "scene_revision": binding["scene_revision"],
        "frame_id": binding["frame_id"],
        "calibration_ref": binding["calibration_ref"],
        "candidate_set_ref": "candidate-set://observed-scene/lab-camera-front",
        "candidate_ref": "candidate://observed-reagent-a/grasp-1",
        "candidates": [{
            "candidate_ref": "candidate://observed-reagent-a/grasp-1",
            "entity_ref": binding["entity_ref"],
        }],
        "perception_binding": binding,
        "process_type": "pour",
    }
    result = provider.prepare(request)
    assert result["provider_available"] is True
    assert result["route_arguments"]["destination_ref"] == binding["destination_ref"]
    assert engine.requests[0]["manipulation_target"]["entity_prim_path"] == "/World/measured_source"

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


def test_agent_task_projection_requires_and_preserves_perception_binding(tmp_path):
    profile = _profile(tmp_path)
    binding = _binding(profile)
    projected = project_pour_task(profile, {
        "task_type": "pour_liquid",
        "source_label": "试剂A",
        "destination_label": "烧杯",
        "parameters": {"tilt_rad": 0.87, "hold_s": 0.4},
    }, binding=binding)
    assert "source_path" not in projected
    assert "destination_path" not in projected
    assert projected["binding"] == binding
    assert projected["parameters"] == {"tilt_rad": 0.87, "hold_s": 0.4}
    assert "paos_input" not in projected

    with pytest.raises(LabTaskProjectionError, match="perception binding is required"):
        project_pour_task(profile, {"task_type": "pour_liquid"})

    with pytest.raises(LabTaskProjectionError, match="source label"):
        project_pour_task(profile, {
            "task_type": "pour_liquid", "source_label": "试剂B", "destination_label": "烧杯",
        }, binding=binding)


def test_legacy_cycles_are_not_invoked_from_perception_bound_task_projection(tmp_path):
    engine = FakeEngine()
    bundle = _runtime(tmp_path, engine)
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "object.pour_cycle" not in tools
        assert "tool.stir_cycle" not in tools
        assert "manipulation.cycle" not in tools
        assert "manipulation.execute_subtask" not in tools
        assert not {"object.acquire", "object.place", "object.pour", "tool.stir"} & tools
        for tool_id in ("object.acquire", "object.place", "object.pour", "tool.stir", "manipulation.prepare_held"):
            assert bundle.runtime.get_tool(tool_id)
            with pytest.raises(CapabilityRuntimeError, match="not externally invokable"):
                bundle.runtime.start_action(tool_id, {}, caller_id=CALLER)

        projected = project_pour_task(bundle.engine.profile, {
            "task_type": "pour_liquid", "source_label": "试剂A", "destination_label": "烧杯",
            "parameters": {"tilt_rad": 0.87, "hold_s": 0.4},
        }, binding=_binding(bundle.engine.profile))
        assert projected["binding"]["entity_ref"] == "entity://observed-reagent-a"
        assert "paos_input" not in projected
        assert engine.started == []
    finally:
        bundle.client.close()


def test_labutopia_legacy_cycle_is_not_registered_in_subtask_composition(tmp_path):
    engine = FakeEngine()
    bundle = _runtime(tmp_path, engine)
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "object.pour_cycle" not in tools
        with pytest.raises(CapabilityRuntimeError, match="unknown ToolSpec"):
            bundle.runtime.start_action("object.pour_cycle", {}, caller_id=CALLER)
        assert engine.started == []
    finally:
        bundle.client.close()


def test_labutopia_composition_owns_default_durable_assignment_store(tmp_path):
    engine = FakeEngine()
    bundle = _runtime(tmp_path, engine)
    store_path = tmp_path / "outputs" / "paos" / "assignment-artifacts.sqlite3"
    assert store_path.is_file()
    assert bundle.client._owns_assignment_store is True
    bundle.client.close()
    from pick_place_workflow.persistent_runtime import SQLiteAssignmentArtifactStore

    with SQLiteAssignmentArtifactStore(store_path) as reopened:
        assert reopened.get("artifact://missing/assignment") is None


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


def test_delayed_camera_session_can_register_queries_but_capture_still_fails_closed(tmp_path):
    engine = FakeEngine()
    profile = _profile(tmp_path)
    engine.profile = profile
    provider = GenericProvider()

    class DelayedObservationSource:
        observation_ready = False

        def capture(self, request):
            return {"sensor_available": False}

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
        observation_source=DelayedObservationSource(),
        resolve_preparation=lambda operation, arguments: dict(arguments),
        tool_context_provider=lambda _: {"ready": True},
        allow_live=False,
        perception_adapter=adapter,
        subtask_context_resolver=lambda _caller: {},
    )
    try:
        tools = {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]}
        assert "scene.observe" in tools
        assert "manipulation.execute_subtask" in tools
        observed = bundle.runtime.invoke_query("scene_observation", "observe", {
            "sensor_ref": "camera/front",
            "max_age_ms": 1000,
        })
        assert observed["status"] == "unavailable"
        assert observed["error"]["code"] == "sensor_unavailable"
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


def test_client_never_falls_back_from_phase_action_to_legacy_cycle(tmp_path):
    engine = FakeEngine()
    client = LabUtopiaCycleClient(engine, allow_live=True)
    try:
        with pytest.raises(LabUtopiaPAOSClientError, match="phase-level execution is unavailable"):
            client.start("pour", "invocation://manipulation-pour/1", "paos:task-1", {
                "entity_ref": "entity://observed-reagent-a",
                "scene_revision": "scene-1",
            })
        assert engine.started == []
    finally:
        client.close()
