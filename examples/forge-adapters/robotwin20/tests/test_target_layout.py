import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from robotwin20_adapter.target_layout import ObservedLayout, bind_entities


def pose(x, y=0, z=1):
    result = np.eye(4)
    result[:3, 3] = [x, y, z]
    return result.reshape(-1).tolist()


def fixture(tmp_path):
    identity = {"observation_ref": "observation://s1/camera", "scene_revision": "s1",
                "calibration_ref": "artifact://capture/calibration"}
    (tmp_path / "capture").mkdir()
    (tmp_path / "capture/calibration.json").write_text(json.dumps({
        "camera_name": "camera", "extrinsic_cv": np.eye(4).tolist(),
    }))
    objects = [{"entity_ref": f"entity://execution-{i}", "actor_name": f"actor{i}",
                "half_extents_m": [.04, .04, .04], "world_T_object": pose(x),
                "world_T_functional_point": pose(x), "target_ref": "destination://benchmark-answer"}
               for i, x in enumerate([0., .2, .4])]
    envelopes = [{"entity_ref": f"entity://seen-{i}", "frame_id": "camera", "unit": "m",
                  "min_xyz_m": [x-.02, -.02, .98], "max_xyz_m": [x+.02, .02, 1.02]}
                 for i, x in enumerate([0., .2, .4])]

    class Client:
        revision = "s1"
        calls = []

        def query(self, operation, arguments):
            self.calls.append(operation)
            return {"scene_revision": self.revision}

    source = {**identity, "objects": objects}
    client = Client()
    layout = ObservedLayout(client, tmp_path, lambda _: deepcopy(source))
    layout.remember({}, {**identity, "status": "available",
                        "captured_at": datetime.now(timezone.utc).isoformat()})
    layout.remember({}, {**identity, "status": "available", "frame": {"frame_id": "camera"},
                        "entities": [{"entity_ref": e["entity_ref"]} for e in envelopes],
                        "spatial_envelopes": envelopes, "ambiguities": []})
    request = {**identity, "ordered_entities": [e["entity_ref"] for e in reversed(envelopes)],
               "axis": "world+x", "max_age_ms": 60000}
    return layout, request, source, envelopes


def test_layout_uses_observed_order_not_benchmark_targets(tmp_path):
    layout, request, source, _ = fixture(tmp_path)
    result = layout.invoke(request)
    assert result["status"] == "available"
    assert result["motion_authorized"] is False
    assert [t["entity_ref"] for t in result["targets"]] == request["ordered_entities"]
    assert [t["world_T_object_target"][3] for t in result["targets"]] == [0, .2, .4]
    assert "benchmark-answer" not in json.dumps(result)
    facts = layout.scene_facts({**request, "destination_ref": result["targets"][0]["destination_ref"]})
    assert facts["objects"][0]["actor_name"] == "actor2"
    assert facts["objects"][0]["entity_ref"] == "entity://seen-2"
    assert source["objects"][0]["entity_ref"] == "entity://execution-0"
    assert set(layout.client.calls) == {"snapshot", "bind_observed_entities"}


@pytest.mark.parametrize("failure", ["stale", "expired", "calibration", "duplicate", "missing", "axis", "ambiguity"])
def test_layout_rejects_incomplete_or_ambiguous_inputs(tmp_path, failure):
    layout, request, _, _ = fixture(tmp_path)
    key = tuple(request[k] for k in ("observation_ref", "scene_revision", "calibration_ref"))
    if failure == "stale":
        layout.client.revision = "s2"
    elif failure == "expired":
        layout.captures[key] = (datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
    elif failure == "calibration":
        (tmp_path / "capture/calibration.json").write_text('{}')
    elif failure == "duplicate":
        request["ordered_entities"] = ["entity://seen-0"]*2
    elif failure == "missing":
        layout.observations.clear()
    elif failure == "axis":
        request["axis"] = "image-left"
    else:
        layout.observations[key]["ambiguities"] = [{"reason": "occlusion"}]
    assert layout.invoke(request)["status"] == "unavailable"
    assert not layout.layouts
    assert "bind_observed_entities" not in layout.client.calls


def test_binding_rejects_competing_and_many_to_one_objects(tmp_path):
    _, _, source, envelopes = fixture(tmp_path)
    objects = source["objects"]
    duplicate = deepcopy(objects[0])
    duplicate["entity_ref"] = "entity://other"
    with pytest.raises(ValueError, match="ambiguous"):
        bind_entities(["entity://seen-0"], envelopes, [*objects, duplicate], np.eye(4))
    duplicate_envelope = {**envelopes[0], "entity_ref": "entity://alias"}
    with pytest.raises(ValueError, match="multiple"):
        bind_entities(["entity://seen-0", "entity://alias"], [*envelopes, duplicate_envelope], objects, np.eye(4))


def test_binding_applies_calibration(tmp_path):
    _, _, source, envelopes = fixture(tmp_path)
    transform = np.eye(4)
    transform[0, 3] = .2
    bound = bind_entities(["entity://seen-0"], envelopes, source["objects"], transform)
    assert bound["entity://seen-0"]["entity_ref"] == "entity://execution-1"


def test_layout_rejects_stale_preparation_and_unknown_destination(tmp_path):
    layout, request, _, _ = fixture(tmp_path)
    result = layout.invoke(request)
    target = result["targets"][0]["destination_ref"]
    with pytest.raises(ValueError, match="current observed layout"):
        layout.scene_facts({**request, "destination_ref": "destination://invented"})
    layout.client.revision = "s2"
    with pytest.raises(ValueError, match="stale"):
        layout.scene_facts({**request, "destination_ref": target})
    assert "bind_observed_entities" not in layout.client.calls


def test_layout_rejects_nonfinite_and_nonrigid_calibration(tmp_path):
    layout, request, _, _ = fixture(tmp_path)
    bad = np.eye(4)
    bad[0, 0] = 2
    (tmp_path / "capture/calibration.json").write_text(json.dumps({
        "camera_name": "camera", "extrinsic_cv": bad.tolist(),
    }))
    assert layout.invoke(request)["status"] == "unavailable"
    assert not layout.layouts


def test_public_transport_exposes_layout_without_motion(tmp_path):
    import asyncio

    from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeTransport
    from PhyAgentOS.forge.tool_client import ForgeToolClient

    from robotwin20_adapter.target_layout import LAYOUT_TOOL_SPEC

    async def exercise():
        layout, request, _, _ = fixture(tmp_path)
        runtime = CapabilityRuntime()
        runtime.register_tool(LAYOUT_TOOL_SPEC, layout, context={"motion_authorized": False})
        transport = CapabilityRuntimeTransport(runtime)
        async with ForgeToolClient("http://layout.test", transport=transport) as client:
            context = await client.get_tool_context("manipulation.layout")
            assert context["data"]["ready"]
            result = await client.invoke_query_tool("manipulation.layout", request, caller_id="test:layout")
        assert result["data"]["status"] == "available"
        assert result["data"]["motion_authorized"] is False
        assert result["data"]["entity_bindings"][0] == {
            "entity_ref": "entity://seen-2", "execution_entity_ref": "entity://execution-2",
        }
        assert set(layout.client.calls) == {"snapshot"}

    asyncio.run(exercise())


def test_worker_binding_preserves_execution_actor_and_rejects_stale_layout(tmp_path):
    from types import SimpleNamespace

    from robotwin_persistent_engine import RoboTwinPersistentEngine
    from robotwin_simulation_probe_worker import _actor_for_entity

    actor = object()
    task = SimpleNamespace(block1=actor)
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.backend = SimpleNamespace(_task=task, snapshot=lambda: {"scene_revision": "s1"})
    directory = tmp_path / "layouts"
    directory.mkdir()
    artifact = {"scene_revision": "s1", "motion_authorized": False, "bindings": [{
        "entity_ref": "entity://observed-9", "execution_entity_ref": "entity://block-red-1",
        "actor_name": "block1",
    }]}
    path = directory / "test.json"
    path.write_text(json.dumps(artifact))
    result = engine.query("bind_observed_entities", {"layout_ref": "artifact://layouts/test"})
    assert result["motion_authorized"] is False
    assert _actor_for_entity(task, "entity://observed-9") is actor
    assert _actor_for_entity(task, "entity://block-red-1") is actor
    artifact["scene_revision"] = "s0"
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="current idle scene"):
        engine.query("bind_observed_entities", {"layout_ref": "artifact://layouts/test"})


def test_layout_preserves_route_scene_and_functional_transform_contract(tmp_path):
    from test_route_inputs import _facts

    from robotwin20_adapter.route_inputs import (
        CURRENT_SCENE_FACTS_SCHEMA_VERSION,
        validate_scene_facts,
    )

    layout, request, source, _ = fixture(tmp_path)
    facts = _facts()
    facts.update({k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")})
    facts.update(schema_version=CURRENT_SCENE_FACTS_SCHEMA_VERSION, observation_frame_id="camera")
    for index, obj in enumerate(source["objects"]):
        obj.update(object_frame_id=f"object-{index}", functional_point_id=0,
                   world_T_functional_point=pose(index*.2, z=.98),
                   world_T_functional_target=pose(index*.2, z=.98),
                   world_T_object_target=pose(index*.2))
    facts["objects"] = source["objects"]
    validate_scene_facts(facts)
    layout.source = lambda _: deepcopy(facts)
    result = layout.invoke(request)
    assert result["status"] == "available"
    routed = layout.scene_facts({**request, "destination_ref": result["targets"][0]["destination_ref"]})
    validate_scene_facts(routed)
    first = routed["objects"][0]
    assert first["world_T_object_target"][3] == 0
    assert first["world_T_functional_target"][11] == .98
