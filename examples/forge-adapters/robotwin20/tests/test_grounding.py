import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeTransport
from PhyAgentOS.forge.tool_client import ForgeToolClient
from pick_place_workflow.grounding import BIND_TOOL_SPEC, TARGET_TOOL_SPEC

from robotwin20_adapter.grounding import Grounding, GroundingEndpoint


def pose(x=0):
    value = np.eye(4)
    value[0, 3] = x
    return value.reshape(-1).tolist()


def setup(tmp_path):
    identity = dict(
        observation_ref="observation://s1/camera",
        scene_revision="s1",
        calibration_ref="artifact://capture/calibration",
    )
    (tmp_path / "capture").mkdir()
    (tmp_path / "capture/calibration.json").write_text(
        json.dumps({"camera_name": "camera", "extrinsic_cv": np.eye(4).tolist()})
    )
    obj = dict(
        entity_ref="entity://execution",
        actor_name="block1",
        half_extents_m=[0.04] * 3,
        world_T_object=pose(),
        world_T_functional_point=pose(),
    )
    facts = {**identity, "objects": [obj]}

    class Client:
        revision = "s1"
        validity = "action_driven"
        holding = "empty"

        def query(self, operation, arguments):
            return dict(
                scene_revision=self.revision,
                scene_validity=self.validity,
                holding_state=self.holding,
            )

    grounding = Grounding(Client(), tmp_path, lambda _: deepcopy(facts))
    grounding.remember(
        "scene.observe",
        {
            **identity,
            "status": "available",
            "frame": {"frame_id": "camera"},
            "captured_at": "2000-01-01T00:00:00Z",
        },
    )
    grounding.remember(
        "scene.understand",
        {
            **identity,
            "status": "available",
            "frame": {"frame_id": "camera"},
            "entities": [{"entity_ref": "entity://seen"}],
            "ambiguities": [],
            "derived_artifacts": [{
                "artifact_ref": "artifact://capture/geometry",
                "kind": "object_geometry",
                "entity_ref": "entity://seen",
                "descriptor": {"dimensions_m": [0.04, 0.04, 0.04]},
            }],
            "spatial_envelopes": [
                dict(
                    entity_ref="entity://seen",
                    frame_id="camera",
                    unit="m",
                    min_xyz_m=[-0.02] * 3,
                    max_xyz_m=[0.02] * 3,
                )
            ],
        },
    )
    return grounding, {**identity, "entity_refs": ["entity://seen"]}, facts


def test_single_object_binding_needs_no_goal_and_target_preserves_explicit_pose(tmp_path):
    g, request, _ = setup(tmp_path)
    bound = g.bind(request)
    assert not g.targets
    assert bound["entities"][0]["entity_ref"] == "entity://seen"
    assert bound["entities"][0]["half_extents_m"] == pytest.approx([0.02, 0.02, 0.02])
    target = g.target(
        dict(
            binding_ref=bound["binding_ref"],
            entity_ref="entity://seen",
            frame_id="world",
            unit="m",
            frame_T_object_target=pose(0.35),
        )
    )
    assert target["world_T_object_target"] == pose(0.35)
    facts = g.scene_facts(
        {**request, "intent": {"entity_ref": "entity://seen"}, "destination_ref": target["destination_ref"]}
    )
    assert facts["objects"][0]["world_T_object_target"] == pose(0.35)
    assert facts["objects"][0]["actor_name"] == "block1"
    assert target["motion_authorized"] is False


def test_oracle_scene_uses_bound_actor_geometry_without_changing_observed_identity(tmp_path):
    g, request, _ = setup(tmp_path)
    bound = g.bind(request)
    target = g.target(
        dict(
            binding_ref=bound["binding_ref"],
            entity_ref="entity://seen",
            frame_id="world",
            unit="m",
            frame_T_object_target=pose(0.35),
        )
    )

    facts = g.oracle_scene_facts(
        {
            **request,
            "intent": {"entity_ref": "entity://seen"},
            "destination_ref": target["destination_ref"],
        }
    )

    assert facts["objects"] == [
        {
            "entity_ref": "entity://seen",
            "actor_name": "block1",
            "half_extents_m": [0.04, 0.04, 0.04],
            "world_T_object": pose(),
            "world_T_functional_point": pose(),
            "target_ref": target["destination_ref"],
            "world_T_object_target": pose(0.35),
            "world_T_functional_target": pose(0.35),
        }
    ]
    assert facts["geometry_source"] == "oracle_actor"
    assert "observed_collision" not in facts


def test_oracle_grasp_activation_reuses_one_current_persisted_binding(tmp_path):
    grounding, request, _ = setup(tmp_path)
    bound = grounding.bind(request)
    calls = []

    def query(operation, arguments):
        calls.append((operation, arguments))
        if operation == "snapshot":
            return {
                "scene_revision": "s1",
                "scene_validity": "action_driven",
                "holding_state": "empty",
            }
        assert operation == "bind_observed_entities"
        return {"scene_revision": "s1", "motion_authorized": False}

    grounding.client.query = query
    reference = grounding.activate_observed_entities(
        {
            **{key: request[key] for key in ("observation_ref", "scene_revision", "calibration_ref")},
            "targets": [{"entity_ref": "entity://seen"}],
        }
    )

    assert reference == bound["binding_ref"]
    assert calls[-1] == (
        "bind_observed_entities",
        {"binding_ref": bound["binding_ref"]},
    )


@pytest.mark.parametrize("change", ["unchanged", "translated", "rotated", "missing", "invalid", "duplicate", "nonfinite"])
def test_grounding_binding_checks_captured_actor_pose_not_visual_frame(tmp_path, monkeypatch, change):
    import robotwin_persistent_engine as engine_module

    g, request, facts = setup(tmp_path)
    # A rotated actor and biased visual centre reproduce the real frame mismatch.
    captured = np.eye(4)
    captured[:2, :2] = [[0, -1], [1, 0]]
    captured[0, 3] = 0.007
    facts["objects"][0]["world_T_object"] = captured.reshape(-1).tolist()
    bound = g.bind(request)
    assert bound["entities"][0]["world_T_object"] != captured.reshape(-1).tolist()
    binding_path = tmp_path / (bound["binding_ref"].removeprefix("artifact://") + ".json")
    saved = json.loads(binding_path.read_text())
    assert saved["scene_facts"]["objects"][0]["world_T_object"] == captured.reshape(-1).tolist()
    if change == "missing":
        saved["scene_facts"]["objects"] = []
    elif change == "invalid":
        saved["scene_facts"]["objects"][0]["world_T_object"] = [0]
    elif change == "duplicate":
        saved["scene_facts"]["objects"] *= 2
    elif change == "nonfinite":
        saved["scene_facts"]["objects"][0]["world_T_object"][0] = float("nan")
    binding_path.write_text(json.dumps(saved))
    current = captured.copy()
    if change == "translated":
        current[0, 3] += 0.002
    elif change == "rotated":
        current[:3, :3] = np.eye(3)
    actor = SimpleNamespace(get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: current))
    old_mapping = {"previous": object()}
    runtime_task = SimpleNamespace(block1=actor, _paos_observed_entities=old_mapping)
    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=runtime_task, snapshot=lambda: {"scene_revision": "s1"})
    monkeypatch.setattr(engine_module.probe, "_actor_for_entity", lambda task, ref: actor)
    if change == "unchanged":
        result = engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})
        assert result["motion_authorized"] is False
        assert runtime_task._paos_observed_entities == {"entity://seen": actor}
    else:
        error = engine_module.BindingPoseChangedError if change in {"translated", "rotated"} else engine_module.BindingPoseUnavailableError
        with pytest.raises(error):
            engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})
        assert runtime_task._paos_observed_entities is old_mapping


def test_binding_rejection_does_not_publish_partial_entity_aliases(tmp_path, monkeypatch):
    import robotwin_persistent_engine as module

    g, request, _ = setup(tmp_path)
    bound = g.bind(request)
    path = tmp_path / (bound["binding_ref"].removeprefix("artifact://") + ".json")
    value = json.loads(path.read_text())
    value["bindings"].append({
        "entity_ref": "entity://second", "execution_entity_ref": "entity://execution-second", "actor_name": "block2",
    })
    value["scene_facts"]["objects"].append({
        "entity_ref": "entity://execution-second", "actor_name": "block2", "world_T_object": pose(),
    })
    path.write_text(json.dumps(value))
    first = SimpleNamespace(get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.eye(4)))
    second = SimpleNamespace(get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.array(pose(0.1)).reshape(4, 4)))
    old = {"previous": first}
    runtime_task = SimpleNamespace(block1=first, block2=second, _paos_observed_entities=old)
    engine = object.__new__(module.RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=runtime_task, snapshot=lambda: {"scene_revision": "s1"})
    actors = {"entity://execution": first, "entity://execution-second": second}
    monkeypatch.setattr(module.probe, "_actor_for_entity", lambda task, ref: actors[ref])
    with pytest.raises(module.BindingPoseChangedError):
        engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})
    assert runtime_task._paos_observed_entities is old


def _rewrite_binding_identity(tmp_path, bound, *, observed_ref, execution_ref, actor_name):
    path = tmp_path / (bound["binding_ref"].removeprefix("artifact://") + ".json")
    value = json.loads(path.read_text())
    original_ref = value["bindings"][0]["entity_ref"]
    value["bindings"][0] = {
        "entity_ref": observed_ref,
        "execution_entity_ref": execution_ref,
        "actor_name": actor_name,
    }
    value["objects"][observed_ref] = value["objects"].pop(original_ref)
    value["scene_facts"]["objects"][0].update(
        entity_ref=execution_ref,
        actor_name=actor_name,
    )
    path.write_text(json.dumps(value))


def test_same_reserved_observed_and_execution_identity_is_accepted(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    grounding, request, _ = setup(tmp_path)
    bound = grounding.bind(request)
    _rewrite_binding_identity(
        tmp_path,
        bound,
        observed_ref="entity://block-green-1",
        execution_ref="entity://block-green-1",
        actor_name="block2",
    )
    actor = SimpleNamespace(
        get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.eye(4))
    )
    old = {"previous": object()}
    runtime_task = SimpleNamespace(block2=actor, _paos_observed_entities=old)
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=runtime_task, snapshot=lambda: {"scene_revision": "s1"})

    result = engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})

    assert result == {"scene_revision": "s1", "motion_authorized": False}
    assert runtime_task._paos_observed_entities == {"entity://block-green-1": actor}


@pytest.mark.parametrize(
    ("execution_ref", "actor_name"),
    [
        ("entity://block-red-1", "block1"),
        ("entity://block-green-1", "block1"),
    ],
)
def test_reserved_observed_identity_rejects_execution_or_actor_mismatch(
    tmp_path, execution_ref, actor_name
):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    grounding, request, _ = setup(tmp_path)
    bound = grounding.bind(request)
    _rewrite_binding_identity(
        tmp_path,
        bound,
        observed_ref="entity://block-green-1",
        execution_ref=execution_ref,
        actor_name=actor_name,
    )
    actor = SimpleNamespace(
        get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.eye(4))
    )
    old = {"previous": actor}
    runtime_task = SimpleNamespace(
        block1=actor,
        block2=actor,
        _paos_observed_entities=old,
    )
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=runtime_task, snapshot=lambda: {"scene_revision": "s1"})

    with pytest.raises(ValueError, match="reserved observed identity differs"):
        engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})
    assert runtime_task._paos_observed_entities is old


def test_duplicate_binding_correspondence_does_not_publish_partial_aliases(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    grounding, request, _ = setup(tmp_path)
    bound = grounding.bind(request)
    path = tmp_path / (bound["binding_ref"].removeprefix("artifact://") + ".json")
    value = json.loads(path.read_text())
    value["bindings"].append(
        {
            "entity_ref": "entity://second",
            "execution_entity_ref": value["bindings"][0]["execution_entity_ref"],
            "actor_name": "block1",
        }
    )
    path.write_text(json.dumps(value))
    actor = SimpleNamespace(
        get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.eye(4))
    )
    old = {"previous": actor}
    runtime_task = SimpleNamespace(block1=actor, _paos_observed_entities=old)
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=runtime_task, snapshot=lambda: {"scene_revision": "s1"})

    with pytest.raises(ValueError, match="one-to-one"):
        engine.query("bind_observed_entities", {"binding_ref": bound["binding_ref"]})
    assert runtime_task._paos_observed_entities is old


def test_preparation_grounding_propagates_deadline_to_both_worker_queries(tmp_path):
    from robotwin20_adapter.preparation_deadline import PreparationDeadline

    g, request, _ = setup(tmp_path)
    bound = g.bind(request)
    target = g.target(dict(
        **{k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")},
        binding_ref=bound["binding_ref"], entity_ref="entity://seen", frame_id="world",
        unit="m", frame_T_object_target=pose(0.35),
    ))
    original = g.client.query
    calls = []

    def query(operation, arguments, *, timeout_s):
        assert 0 < timeout_s <= 10
        calls.append((operation, timeout_s))
        return original(operation, arguments)

    g.client.query = query
    g.scene_facts(
        {**request, "intent": {"entity_ref": "entity://seen"}, "destination_ref": target["destination_ref"]},
        deadline=PreparationDeadline.start(10),
    )
    assert [op for op, _ in calls] == ["snapshot", "bind_observed_entities"]
    assert calls[1][1] < calls[0][1]


@pytest.mark.parametrize("code", [
    "object_shape_uncertain",
    "metric_3d_unavailable",
    "metric_geometry_unavailable",
    "NO_RELIABLE_METRIC_EXTENTS",
])
def test_later_stage_visual_ambiguity_is_not_a_binding_gate(tmp_path, code):
    g, request, _ = setup(tmp_path)
    g.understandings[(request["observation_ref"], request["scene_revision"], request["calibration_ref"])] ["ambiguities"] = [
        {"code": code, "message": "visual evidence requires later-stage checks", "entity_refs": ["entity://seen"]}
    ]
    bound = g.bind(request)
    assert bound["status"] == "available"


def test_unselected_entity_ambiguity_does_not_block_selected_binding(tmp_path):
    g, request, _ = setup(tmp_path)
    g.understandings[(request["observation_ref"], request["scene_revision"], request["calibration_ref"])] ["ambiguities"] = [
        {
            "code": "entity_pose_ambiguous",
            "message": "another entity is unresolved",
            "entity_refs": ["entity://other"],
        }
    ]
    bound = g.bind(request)
    assert bound["status"] == "available"


def test_binding_diagnostics_identify_entity_scoped_blocking_ambiguity(tmp_path):
    g, request, _ = setup(tmp_path)
    g.understandings[(request["observation_ref"], request["scene_revision"], request["calibration_ref"])] ["ambiguities"] = [
        {
            "code": "entity_pose_ambiguous",
            "message": "execution identity is unresolved",
            "entity_refs": ["entity://seen"],
        }
    ]
    result = GroundingEndpoint(g.bind).invoke(request)
    assert result["status"] == "unavailable"
    assert result["error"]["code"] == "grounding_unavailable"
    assert result["diagnostics"] == {
        "stage": "ambiguity_admission",
        "message": "selected entity has unresolved perception ambiguity",
        "selected_entities": ["entity://seen"],
        "blocking_ambiguities": [{
            "code": "entity_pose_ambiguous",
            "entity_refs": ["entity://seen"],
            "message": "execution identity is unresolved",
        }],
        "deferred_ambiguities": [],
    }


def test_binding_diagnostics_report_invalid_entity_refs_shape(tmp_path):
    g, request, _ = setup(tmp_path)
    request["entity_refs"] = "entity://seen"
    result = GroundingEndpoint(g.bind).invoke(request)
    assert result["status"] == "unavailable"
    assert result["diagnostics"] == {
        "stage": "input_validation",
        "message": "entity_refs must be a non-empty array of references",
        "selected": "entity://seen",
    }


def test_binding_projects_visual_geometry_with_camera_rotation(tmp_path):
    g, request, facts = setup(tmp_path)
    facts["objects"][0]["half_extents_m"] = [1.0, 1.0, 1.0]
    calibration = np.eye(4)
    calibration[:3, :3] = np.asarray([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
    (tmp_path / "capture/calibration.json").write_text(
        json.dumps({"camera_name": "camera", "extrinsic_cv": calibration.tolist()})
    )
    g.understandings[(request["observation_ref"], request["scene_revision"], request["calibration_ref"])] [
        "spatial_envelopes"
    ][0].update(min_xyz_m=[0.0, 0.0, 0.0], max_xyz_m=[0.1, 0.2, 0.3])
    bound = g.bind(request)
    pose_world = np.asarray(bound["entities"][0]["world_T_object"]).reshape(4, 4)
    assert pose_world[:3, :3].tolist() == np.linalg.inv(calibration)[:3, :3].tolist()
    assert pose_world[:3, 3].tolist() == pytest.approx([0.1, -0.05, 0.15])


def test_binding_uses_metric_envelope_when_optional_shape_artifact_is_absent(tmp_path):
    g, request, _ = setup(tmp_path)
    understanding = next(iter(g.understandings.values()))
    understanding["derived_artifacts"] = []
    bound = g.bind(request)
    assert bound["status"] == "available"
    assert bound["entities"][0]["half_extents_m"] == pytest.approx([0.02, 0.02, 0.02])


def test_binding_diagnostics_report_current_scene_mismatch(tmp_path):
    g, request, _ = setup(tmp_path)
    g.client.revision = "s2"
    result = GroundingEndpoint(g.bind).invoke(request)
    assert result["status"] == "unavailable"
    assert result["diagnostics"]["stage"] == "current_scene"
    assert result["diagnostics"]["expected"]["scene_revision"] == "s1"
    assert result["diagnostics"]["actual"]["scene_revision"] == "s2"


def test_binding_rejects_malformed_object_geometry_instead_of_falling_back(tmp_path):
    g, request, _ = setup(tmp_path)
    understanding = next(iter(g.understandings.values()))
    understanding["derived_artifacts"][0]["descriptor"] = {"dimensions_m": [0.04, 0.04]}
    result = GroundingEndpoint(g.bind).invoke(request)
    assert result["status"] == "unavailable"
    assert result["diagnostics"]["stage"] == "visual_geometry"
    assert result["diagnostics"]["geometry_artifact_present"] is True


def test_persistent_snapshot_declares_action_driven_validity_without_executing():
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.backend = SimpleNamespace(snapshot=lambda: {"scene_revision": "idle-1"})
    assert engine.query("snapshot", {}) == {"scene_revision": "idle-1", "scene_validity": "action_driven"}


def test_real_route_builder_consumes_target_from_nested_intent(tmp_path, monkeypatch):
    from test_persistent_route_builder import setup_builder

    from robotwin20_adapter.route_inputs import CURRENT_SCENE_FACTS_SCHEMA_VERSION

    request, builder, _ = setup_builder(tmp_path, monkeypatch)
    facts = builder.scene_source(request)
    facts["schema_version"] = CURRENT_SCENE_FACTS_SCHEMA_VERSION
    obj = facts["objects"][0]
    ref = request["intent"]["entity_ref"]
    center = np.asarray(obj["world_T_object"]).reshape(4, 4)[:3, 3]
    facts["objects"] = [{k: v for k, v in obj.items() if "target" not in k}]
    calibration_path = tmp_path / (request["calibration_ref"].removeprefix("artifact://") + ".json")
    calibration_path.parent.mkdir(parents=True, exist_ok=True)
    calibration_path.write_text(json.dumps({"camera_name": "head_camera", "extrinsic_cv": np.eye(4).tolist()}))
    builder.client.snapshot["scene_validity"] = "action_driven"
    g = Grounding(builder.client, tmp_path, lambda _: deepcopy(facts))
    identities = {k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")}
    g.remember("scene.observe", {**identities, "status": "available", "frame": {"frame_id": "head_camera"},
                                "captured_at": "2000-01-01T00:00:00Z"})
    g.remember("scene.understand", {**identities, "status": "available", "frame": {"frame_id": "head_camera"},
        "entities": [{"entity_ref": ref}], "ambiguities": [], "spatial_envelopes": [{
            "entity_ref": ref, "frame_id": "head_camera", "unit": "m",
            "min_xyz_m": (center-.01).tolist(), "max_xyz_m": (center+.01).tolist()}],
        "derived_artifacts": [{"entity_ref": ref, "kind": "object_geometry",
            "descriptor": {"dimensions_m": [0.02, 0.02, 0.02]}}]})
    b = g.bind({**identities, "entity_refs": [ref]})
    target = g.target(dict(binding_ref=b["binding_ref"], entity_ref=ref, frame_id="world",
                           unit="m", frame_T_object_target=obj["world_T_object_target"]))
    request["destination_ref"] = target["destination_ref"]
    builder.scene_source = g.scene_facts

    class ReachedMaterializerError(Exception):
        pass

    def materialize(argv, **kwargs):
        from pathlib import Path
        arguments = dict(zip(argv[1::2], argv[2::2]))
        routed = json.loads(Path(arguments["--scene-facts"]).read_text())
        assert routed["objects"][0]["entity_ref"] == ref
        assert routed["objects"][0]["target_ref"] == target["destination_ref"]
        assert "entity_ref" not in request
        raise ReachedMaterializerError

    monkeypatch.setattr("subprocess.run", materialize)
    with pytest.raises(ReachedMaterializerError):
        builder.build(request)


@pytest.mark.parametrize(
    "failure", ["revision", "holding", "clock_driven", "ambiguous", "missing", "calibration"]
)
def test_binding_rejects_unusable_scene_without_creating_receipt(tmp_path, failure):
    g, req, facts = setup(tmp_path)
    if failure == "revision":
        g.client.revision = "s2"
    if failure == "holding":
        g.client.holding = "holding"
    if failure == "clock_driven":
        g.client.validity = "clock_driven"
    if failure == "ambiguous":
        facts["objects"].append({**facts["objects"][0], "entity_ref": "other"})
    if failure == "missing":
        req["entity_refs"] = ["missing"]
    if failure == "calibration":
        (tmp_path / "capture/calibration.json").write_text("{}")
    assert GroundingEndpoint(g.bind).invoke(req)["status"] == "unavailable"
    assert not g.bindings


def test_target_transform_and_stale_preparation(tmp_path):
    g, req, _ = setup(tmp_path)
    (tmp_path / "capture/calibration.json").write_text(
        json.dumps({"camera_name": "camera", "extrinsic_cv": np.eye(4).tolist()})
    )
    b = g.bind(req)
    g.bindings[b["binding_ref"]]["world_T_observation"] = pose(0.2)
    args = dict(
        binding_ref=b["binding_ref"],
        entity_ref="entity://seen",
        frame_id="camera",
        unit="m",
        frame_T_object_target=pose(0.3),
    )
    t = g.target(args)
    assert t["world_T_object_target"] == pose(0.5)
    args["frame_id"] = "unknown"
    assert GroundingEndpoint(g.target).invoke(args)["status"] == "unavailable"
    g.client.revision = "s2"
    with pytest.raises(ValueError):
        g.scene_facts(
            {**req, "intent": {"entity_ref": "entity://seen"}, "destination_ref": t["destination_ref"]}
        )


def test_public_queries_are_independent_and_do_not_accept_ordering(tmp_path):
    async def run():
        g, req, _ = setup(tmp_path)
        runtime = CapabilityRuntime()
        for spec, resolver in ((BIND_TOOL_SPEC, g.bind), (TARGET_TOOL_SPEC, g.target)):
            runtime.register_tool(
                spec, GroundingEndpoint(resolver), context={"motion_authorized": False}
            )
        async with ForgeToolClient(
            "http://test", transport=CapabilityRuntimeTransport(runtime)
        ) as client:
            result = await client.invoke_query_tool("scene.bind", req)
            assert result["data"]["status"] == "available"
            assert "ordered_entities" not in BIND_TOOL_SPEC["input_schema"]["properties"]
            assert "axis" not in TARGET_TOOL_SPEC["input_schema"]["properties"]

    asyncio.run(run())


def test_worker_rechecks_actor_geometry_before_alias_binding(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine
    from robotwin_simulation_probe_worker import _actor_for_entity

    g, req, _ = setup(tmp_path)
    b = g.bind(req)
    path = tmp_path / (b["binding_ref"].removeprefix("artifact://") + ".json")
    record = json.loads(path.read_text())
    record["bindings"][0]["execution_entity_ref"] = "entity://block-red-1"
    record["scene_facts"]["objects"][0]["entity_ref"] = "entity://block-red-1"
    path.write_text(json.dumps(record))
    actor = SimpleNamespace(
        get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: np.eye(4))
    )
    task = SimpleNamespace(block1=actor)
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=task, snapshot=lambda: {"scene_revision": "s1"})
    engine.query("bind_observed_entities", {"binding_ref": b["binding_ref"]})
    assert _actor_for_entity(task, "entity://seen") is actor
    actor.get_pose = lambda: SimpleNamespace(
        to_transformation_matrix=lambda: np.asarray(pose(0.1)).reshape(4, 4)
    )
    with pytest.raises(ValueError, match="moved"):
        engine.query("bind_observed_entities", {"binding_ref": b["binding_ref"]})


def test_route_contract_uses_observed_geometry_without_hidden_functional_offset(tmp_path):
    from test_route_inputs import _facts

    from robotwin20_adapter.route_inputs import (
        CURRENT_SCENE_FACTS_SCHEMA_VERSION,
        validate_scene_facts,
    )

    g, req, source = setup(tmp_path)
    facts = _facts()
    facts.update({k: req[k] for k in ("observation_ref", "scene_revision", "calibration_ref")})
    facts.update(schema_version=CURRENT_SCENE_FACTS_SCHEMA_VERSION, observation_frame_id="camera")
    obj = source["objects"][0]
    obj.update(
        object_frame_id="execution", functional_point_id=0, world_T_functional_point=pose(0.01)
    )
    obstacles = [facts["objects"][0], facts["objects"][2]]
    for obstacle in obstacles:
        for field in ("target_ref", "world_T_object_target", "world_T_functional_target"):
            obstacle.pop(field)
    facts["objects"] = [obj, *obstacles]
    g.source = lambda _: deepcopy(facts)
    understanding = next(iter(g.understandings.values()))
    for i, obstacle in enumerate(obstacles):
        ref = f"entity://observed-obstacle-{i}"
        center = np.asarray(obstacle["world_T_object"]).reshape(4, 4)[:3, 3] + 0.003
        understanding["entities"].append({"entity_ref": ref})
        understanding["spatial_envelopes"].append({
            "entity_ref": ref, "frame_id": "camera", "unit": "m",
            "min_xyz_m": (center - 0.025).tolist(), "max_xyz_m": (center + 0.025).tolist(),
        })
        req["entity_refs"].append(ref)
    b = g.bind(req)
    t = g.target(
        dict(
            binding_ref=b["binding_ref"],
            entity_ref="entity://seen",
            frame_id="world",
            unit="m",
            frame_T_object_target=pose(0.25),
        )
    )
    route = g.scene_facts(
        {**req, "intent": {"entity_ref": "entity://seen"}, "destination_ref": t["destination_ref"]}
    )
    validate_scene_facts(route)
    assert route["objects"][0]["world_T_functional_target"][3] == 0.25
    assert route["objects"][0]["world_T_object_target"][3] == 0.25
    assert "target_ref" not in obj
    assert route["geometry_source"] == "observation"
    assert route["objects"][1:] != obstacles
    assert all(item["half_extents_m"] == pytest.approx([0.025] * 3) for item in route["objects"][1:])
    assert len(route["objects"]) == 3
    from robotwin20_adapter.collision_world import build_collision_world
    world = build_collision_world(
        route, target_entity_ref="entity://seen", source_scene_facts_ref="artifact://scene/facts",
        geometry_refs={item["entity_ref"]: f"artifact://geometry/{item['actor_name']}" for item in route["objects"]},
        calibration_ref=route["calibration_ref"],
    )
    assert world["obstacle_count"] == 2


@pytest.mark.parametrize("failure", ["many_to_one", "nonrigid", "nan", "wrong_entity"])
def test_correspondence_and_target_fail_closed(tmp_path, failure):
    g, req, _ = setup(tmp_path)
    if failure == "many_to_one":
        u = next(iter(g.understandings.values()))
        u["entities"].append({"entity_ref": "entity://second"})
        u["spatial_envelopes"].append(
            {**u["spatial_envelopes"][0], "entity_ref": "entity://second"}
        )
        req["entity_refs"].append("entity://second")
        assert GroundingEndpoint(g.bind).invoke(req)["status"] == "unavailable"
        return
    b = g.bind(req)
    p = pose()
    if failure == "nonrigid":
        p[0] = 2
    if failure == "nan":
        p[3] = float("nan")
    args = dict(
        binding_ref=b["binding_ref"],
        entity_ref="entity://seen",
        frame_id="world",
        unit="m",
        frame_T_object_target=p,
    )
    if failure == "wrong_entity":
        args["entity_ref"] = "entity://other"
    assert GroundingEndpoint(g.target).invoke(args)["status"] == "unavailable"
    assert not g.targets
