from datetime import datetime, timezone

import pytest

from PhyAgentOS.forge.capability_runtime import (
    OBSERVATION_TOOL_SPEC,
    CapabilityRuntime,
    ObservationContractError,
    ObservationEndpoint,
)


class Source:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def capture(self, request):
        self.calls += 1
        return self.value


class FailingSource:
    def capture(self, request):
        raise RuntimeError("private provider detail")


def observation(**overrides):
    value = {
        "captured_at": datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc),
        "scene_revision": "scene-1",
        "frame_id": "camera-front",
        "calibration_ref": "calibration://front/v1",
        "artifacts": [{"ref": "artifact://scene-1/rgb", "kind": "rgb", "media_type": "image/jpeg"}],
    }
    value.update(overrides)
    return value


def observation_set(*, second_scene="scene-1", second_calibration="calibration://wrist/v1", skew_ms=5):
    return {
        "views": [
            {**observation(), "sensor_ref": "camera/front"},
            {
                **observation(
                    captured_at=datetime(2026, 9, 4, 0, 0, 0, skew_ms * 1000, tzinfo=timezone.utc),
                    scene_revision=second_scene,
                    frame_id="camera-wrist",
                    calibration_ref=second_calibration,
                    artifacts=[{
                        "ref": "artifact://scene-1/wrist/rgb",
                        "kind": "rgb",
                        "media_type": "image/jpeg",
                    }],
                ),
                "sensor_ref": "camera/wrist",
            },
        ]
    }


def test_observation_endpoint_projects_adapter_capture_and_freshness():
    source = Source(observation())
    endpoint = ObservationEndpoint(
        source,
        now=lambda: datetime(2026, 9, 4, 0, 0, 0, 500000, tzinfo=timezone.utc),
    )
    result = endpoint.invoke({"sensor_ref": "camera/front", "max_age_ms": 1000})
    assert result["status"] == "available"
    assert result["observation_ref"] == "observation://scene-1/camera-front"
    assert result["freshness_ms"] == 500
    assert source.calls == 1


def test_observation_endpoint_projects_synchronized_ordered_views():
    source = Source(observation_set())
    result = ObservationEndpoint(
        source,
        now=lambda: datetime(2026, 9, 4, 0, 0, 0, 500000, tzinfo=timezone.utc),
    ).invoke({
        "sensor_refs": ["camera/front", "camera/wrist"],
        "max_age_ms": 1000,
        "max_capture_skew_ms": 10,
    })

    assert result["status"] == "available"
    assert [item["sensor_ref"] for item in result["views"]] == ["camera/front", "camera/wrist"]
    assert result["capture_skew_ms"] == 5
    assert [item["ref"] for item in result["artifacts"]] == [
        "artifact://scene-1/rgb", "artifact://scene-1/wrist/rgb",
    ]


@pytest.mark.parametrize(
    ("arguments", "raw", "code"),
    [
        ({"sensor_refs": ["camera/front", "camera/front"], "max_age_ms": 1000}, observation_set(), "invalid_sensor_ref"),
        ({"sensor_refs": ["camera/front", "camera/wrist"], "max_age_ms": 1000}, observation_set(second_scene="scene-2"), "mixed_scene_revision"),
        ({"sensor_refs": ["camera/front", "camera/wrist"], "max_age_ms": 1000}, observation_set(second_calibration=""), "missing_calibration"),
        ({"sensor_refs": ["camera/front", "camera/wrist"], "max_age_ms": 1000, "max_capture_skew_ms": 4}, observation_set(), "capture_skew_exceeded"),
    ],
)
def test_observation_endpoint_rejects_invalid_observation_sets(arguments, raw, code):
    result = ObservationEndpoint(Source(raw)).invoke(arguments)
    assert result["error"]["code"] == code


def test_observation_endpoint_accepts_the_concrete_returned_frame_id():
    result = ObservationEndpoint(
        Source(observation()),
        now=lambda: datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc),
    ).invoke(
        {
            "sensor_ref": "camera/front",
            "requested_frame": "camera-front",
            "max_age_ms": 1000,
        }
    )
    assert result["status"] == "available"


def test_observation_endpoint_explains_that_abstract_frame_labels_are_invalid():
    result = ObservationEndpoint(Source(observation())).invoke(
        {
            "sensor_ref": "camera/front",
            "requested_frame": "sensor",
            "max_age_ms": 1000,
        }
    )
    assert result["status"] == "invalid"
    assert result["error"] == {
        "code": "invalid_frame",
        "message": (
            "requested_frame must match the concrete Runtime frame_id returned "
            "for sensor_ref; omit it for the initial observation"
        ),
    }


def test_observation_tool_spec_distinguishes_abstract_profile_from_frame_id():
    properties = OBSERVATION_TOOL_SPEC["input_schema"]["properties"]
    assert "concrete Runtime frame_id" in properties["requested_frame"]["description"]
    profile = OBSERVATION_TOOL_SPEC["robot_frame_profile"]
    assert profile["frame_id_source"] == "result.frame.frame_id"
    assert profile["requested_frame_semantics"] == "optional_concrete_runtime_frame_id"
    assert profile["initial_observation"] == "omit_requested_frame"


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (observation(calibration_ref=None), "missing_calibration"),
        (observation(observation_ref="observation://other/frame"), "invalid_observation_binding"),
        (observation(artifacts=[]), "missing_artifacts"),
        (observation(artifacts=[{"ref": "actor://truth", "kind": "state", "media_type": "application/json"}]), "invalid_artifact"),
        (observation(sensor_available=False), "sensor_unavailable"),
    ],
)
def test_observation_endpoint_fails_closed_on_untrusted_adapter_payload(value, code):
    result = ObservationEndpoint(Source(value)).invoke({"sensor_ref": "camera/front", "max_age_ms": 1000})
    assert result["status"] == ("invalid" if code.startswith("invalid") else "unavailable")
    assert result["error"]["code"] == code


def test_observation_endpoint_rejects_invalid_input_before_source_call():
    source = Source(observation())
    result = ObservationEndpoint(source).invoke({"sensor_ref": "", "max_age_ms": 1000})
    assert result["error"]["code"] == "invalid_sensor_ref"
    assert source.calls == 0


def test_observation_endpoint_maps_provider_failure_to_private_unavailable_result():
    def clock():
        return datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)

    result = ObservationEndpoint(FailingSource(), now=clock).invoke(
        {"sensor_ref": "camera/front", "max_age_ms": 1000}
    )
    assert result["status"] == "unavailable"
    assert result["error"] == {
        "code": "sensor_unavailable",
        "message": "observation source failed",
    }
    assert "private provider detail" not in str(result)


def test_observation_tool_spec_registers_explicitly_without_hidden_provider_wiring():
    runtime = CapabilityRuntime()
    runtime.register_tool(
        OBSERVATION_TOOL_SPEC,
        ObservationEndpoint(
            Source(observation()),
            now=lambda: datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc),
        ),
    )
    assert runtime.get_tool("scene.observe")["endpoint_id"] == "scene_observation"
    result = runtime.invoke_query("scene_observation", "observe", {
        "sensor_ref": "camera/front", "max_age_ms": 1000,
    })
    assert result["status"] == "available"


def test_error_projection_uses_injected_clock_and_rejects_naive_clock():
    fixed = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)
    result = ObservationEndpoint(Source(None), now=lambda: fixed).invoke(
        {"sensor_ref": "camera/front", "max_age_ms": 1000}
    )
    assert result["captured_at"] == "2026-09-04T00:00:00Z"
    with pytest.raises(ObservationContractError, match="timezone-aware"):
        ObservationEndpoint(Source(None), now=lambda: datetime(2026, 9, 4)).invoke(
            {"sensor_ref": "camera/front", "max_age_ms": 1000}
        )
