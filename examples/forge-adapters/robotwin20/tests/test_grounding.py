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
            "min_xyz_m": (center-.01).tolist(), "max_xyz_m": (center+.01).tolist()}]})
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


def test_route_contract_uses_only_explicit_goal_and_preserves_functional_offset(tmp_path):
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
    facts["objects"] = [obj]
    g.source = lambda _: deepcopy(facts)
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
    assert route["objects"][0]["world_T_functional_target"][3] == 0.26
    assert route["objects"][0]["world_T_object_target"][3] == 0.25
    assert "target_ref" not in obj


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
