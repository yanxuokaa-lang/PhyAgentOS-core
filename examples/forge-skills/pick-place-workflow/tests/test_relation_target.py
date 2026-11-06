from pick_place_workflow.relation_target import RelationTargetQueryEndpoint


def _request(**overrides):
    return {
        "entity_ref": "entity://stack-block-2",
        "goal_relation": "on",
        "relation_target_ref": "entity://stack-block-1",
        "observation_ref": "observation://scene-8/head_camera",
        "scene_revision": "scene-8",
        "frame_id": "head_camera",
        "calibration_ref": "artifact://scene-8/calibration",
        "freshness_ms": 2,
        "max_age_ms": 1000,
        **overrides,
    }


class _RelationProvider:
    def propose(self, request):
        return {
            **request,
            "status": "available",
            "candidate_set_ref": "relation-target-set://run-1/set-1",
            "candidates": [{
                "candidate_ref": "relation-target://run-1/candidate-1",
                "destination_ref": "destination://run-1/destination-1",
                "world_T_object_target": [
                    1, 0, 0, 0.1,
                    0, 1, 0, 0.2,
                    0, 0, 1, 0.3,
                    0, 0, 0, 1,
                ],
                "evidence_refs": ["artifact://run-1/geometry-1"],
            }],
        }


def test_relation_target_query_is_provider_substitutable_and_never_authorizes_motion():
    result = RelationTargetQueryEndpoint(_RelationProvider()).invoke(_request())

    assert result["status"] == "available"
    assert result["scene_revision"] == "scene-8"
    assert result["candidates"][0]["destination_ref"].startswith("destination://")
    assert result["motion_authorized"] is False


def test_relation_target_query_rejects_stale_observation_before_provider_call():
    class MustNotRun:
        def propose(self, _request):
            raise AssertionError("stale query must not reach the Provider")

    result = RelationTargetQueryEndpoint(MustNotRun()).invoke(
        _request(freshness_ms=1001)
    )

    assert result["status"] == "stale"
    assert result["motion_authorized"] is False


def test_relation_target_query_rejects_provider_scene_drift():
    class Drifted(_RelationProvider):
        def propose(self, request):
            result = super().propose(request)
            result["scene_revision"] = "scene-7"
            return result

    result = RelationTargetQueryEndpoint(Drifted()).invoke(_request())

    assert result["status"] == "stale"
    assert result["candidates"] == []


def test_relation_target_query_rejects_non_rigid_candidate_pose():
    class InvalidPose(_RelationProvider):
        def propose(self, request):
            result = super().propose(request)
            result["candidates"][0]["world_T_object_target"][0] = float("nan")
            return result

    result = RelationTargetQueryEndpoint(InvalidPose()).invoke(_request())

    assert result["status"] == "invalid"
    assert result["candidates"] == []
    assert result["motion_authorized"] is False
