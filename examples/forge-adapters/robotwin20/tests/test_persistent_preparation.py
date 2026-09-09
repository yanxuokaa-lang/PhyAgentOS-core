import json
from copy import deepcopy

import pytest
from test_arm_candidates import _intent, _profile, _result
from test_route_readiness import _request

from robotwin20_adapter.arm_candidates import (
    CompleteRouteSelector,
    build_capability_snapshot,
    enumerate_arm_candidates,
)
from robotwin20_adapter.persistent_preparation import PersistentPreparationProvider
from robotwin20_adapter.prepared_routes import PreparedRoutes
from robotwin20_adapter.route_evidence import _artifact_path


def composition(tmp_path, *, status="pass", node_id="pick-red"):
    intent = _intent().model_copy(update={"node_id": node_id})
    route = _request(tmp_path)
    profile = _profile()
    capability = build_capability_snapshot(
        profile, scene_revision=intent.scene_revision,
        observation_ref=intent.observation_ref, calibration_ref=intent.calibration_ref,
        profile_digest="1" * 64, snapshot_ref="artifact://scene/capability",
    )
    (tmp_path / "scene").mkdir(exist_ok=True)
    (tmp_path / "scene/capability.json").write_text(capability.model_dump_json())
    request = {key: getattr(intent, key) for key in (
        "scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref",
    )}
    request.update(intent=intent.model_dump(mode="json"), frame_id=intent.observation_frame_id,
                   destination_ref="destination://slot", capability_snapshot_ref=capability.snapshot_ref,
                   candidates=deepcopy(route["candidates"]))

    class Client:
        snapshot = {"scene_revision": intent.scene_revision, "holding_state": "empty"}

        def query(self, operation, arguments):
            assert operation == "snapshot"
            return deepcopy(self.snapshot)

    class Builder:
        def build(self, arguments):
            return {"destination_ref": arguments["destination_ref"], "base_request": route,
                    "options": enumerate_arm_candidates(intent, route["candidates"], profile)}

    def evaluate(current_route, option):
        result = _result(current_route, option, status=status)
        result["node_id"] = node_id
        return result

    client = Client()
    routes = PreparedRoutes(client, tmp_path)
    provider = PersistentPreparationProvider(
        client=client, route_builder=Builder(),
        selector=CompleteRouteSelector(evaluate, profile), prepared_routes=routes,
    )
    return request, provider, routes


@pytest.mark.parametrize("node_id", ["pick-red", "pick.red"])
def test_selection_registers_geometry_but_requires_separate_approval(tmp_path, node_id):
    request, provider, routes = composition(tmp_path, node_id=node_id)
    output = provider.prepare(request)
    assignment = output["assignments"][0]
    assert json.loads(_artifact_path(tmp_path, assignment["assignment_ref"]).read_text()) == assignment
    assert assignment["motion_authorized"] is False
    arguments = {key: request[key] for key in (
        "scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref", "frame_id", "capability_snapshot_ref",
    )}
    arguments.update(preparation_ref=f"preparation://{request['scene_revision']}/{request['frame_id']}",
                     candidate_ref=assignment["candidate_ref"], entity_ref=assignment["entity_ref"],
                     assignment_ref=assignment["assignment_ref"])
    with pytest.raises(ValueError, match="no execution approval"):
        routes("acquire", arguments)
    (tmp_path / "scene/approval.json").write_text("{}")
    routes.bind_approval(arguments["preparation_ref"], arguments["candidate_ref"], "artifact://scene/approval")
    assert routes("acquire", arguments)["assignment"] == assignment
    assert provider.prepare(request) == output
    assert routes("acquire", arguments)["approval_ref"] == "artifact://scene/approval"


def test_failed_complete_routes_produce_no_prepared_assignment(tmp_path):
    request, provider, routes = composition(tmp_path, status="fail")
    result = provider.prepare(request)
    assert result["prepared_candidates"] == result["assignments"] == []
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()


@pytest.mark.parametrize("change", ["scene", "holding", "destination"])
def test_changed_world_or_destination_is_not_published(tmp_path, change):
    request, provider, routes = composition(tmp_path)
    original = provider.route_builder.build

    def build(arguments):
        bundle = original(arguments)
        if change == "scene":
            provider.client.snapshot["scene_revision"] = "next-scene"
        elif change == "holding":
            provider.client.snapshot["holding_state"] = "holding"
        else:
            bundle["destination_ref"] = "destination://other"
        return bundle

    provider.route_builder.build = build
    with pytest.raises(ValueError, match="world changed|destination"):
        provider.prepare(request)
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()
