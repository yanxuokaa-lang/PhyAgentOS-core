from copy import deepcopy

import pytest

from robotwin20_adapter.prepared_routes import PreparedRoutes
from test_route_readiness import _request


def test_place_retains_source_geometry_but_requires_current_acquisition(tmp_path):
    route = _request(tmp_path)
    candidate = route["candidates"][0]
    source = {key: route[key] for key in ("scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref")}
    source.update(frame_id=route["observation_frame_id"], preparation_ref="preparation://scene/prepared",
                  candidate_ref=candidate["candidate_ref"], entity_ref=candidate["entity_ref"],
                  assignment_ref="artifact://scene/assignment", capability_snapshot_ref="artifact://scene/capability")

    class Client:
        snapshot = {"scene_revision": route["scene_revision"]}

        def query(self, operation, arguments):
            return deepcopy(self.snapshot)

    client = Client()
    routes = PreparedRoutes(client)
    routes.register(source, route_request=route, approval_ref="artifact://scene/approval", destination_ref="destination://slot")
    assert routes("acquire", source)["scene_revision"] == route["scene_revision"]
    client.snapshot = {"scene_revision": "after-acquire", "acquire_invocation_id": "invocation://acquire/1"}
    with pytest.raises(ValueError, match="stale"):
        routes("acquire", source)
    place = {**source, "destination_ref": "destination://slot", "acquire_invocation_ref": "invocation://acquire/1"}
    resolved = routes("place", place)
    assert resolved["scene_revision"] == "after-acquire"
    assert resolved["route_request"]["scene_revision"] == route["scene_revision"]
    assert resolved["calibration_ref"] == source["calibration_ref"]
    with pytest.raises(ValueError, match="destination"):
        routes("place", {**place, "destination_ref": "destination://other"})
    with pytest.raises(ValueError, match="acquisition"):
        routes("place", {**place, "acquire_invocation_ref": "invocation://acquire/other"})
