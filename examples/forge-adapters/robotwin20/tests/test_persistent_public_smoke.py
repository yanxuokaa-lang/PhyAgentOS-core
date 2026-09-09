from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from check_persistent_runtime import invoke_public_query, select_grasp_target
from PhyAgentOS.forge.capability_runtime import (
    OBSERVATION_TOOL_SPEC,
    CapabilityRuntime,
    ObservationEndpoint,
)


@pytest.mark.asyncio
async def test_public_smoke_captures_fresh_provider_result_on_every_query():
    captures = []

    def capture(request):
        captures.append(request)
        return {
            "captured_at": datetime.now(timezone.utc),
            "scene_revision": "scene-0", "frame_id": "head_camera",
            "calibration_ref": "artifact://scene/calibration",
            "artifacts": [{"ref": f"artifact://scene/capture-{len(captures)}/rgb",
                           "kind": "rgb", "media_type": "image/png"}],
        }

    runtime = CapabilityRuntime()
    runtime.register_tool(OBSERVATION_TOOL_SPEC, ObservationEndpoint(SimpleNamespace(capture=capture)))
    arguments = {"sensor_ref": "camera/head", "max_age_ms": 60000}
    first = await invoke_public_query(runtime, "scene.observe", arguments)
    second = await invoke_public_query(runtime, "scene.observe", arguments)
    assert first["status"] == second["status"] == "available"
    assert first["scene_revision"] == second["scene_revision"]
    assert first["artifacts"] != second["artifacts"]
    assert captures == [arguments, arguments]


@pytest.mark.asyncio
async def test_public_smoke_preserves_unavailable_sensor_result():
    runtime = CapabilityRuntime()
    runtime.register_tool(OBSERVATION_TOOL_SPEC, ObservationEndpoint(SimpleNamespace(capture=lambda request: None)))
    result = await invoke_public_query(runtime, "scene.observe", {"sensor_ref": "camera/head", "max_age_ms": 60000})
    assert result["status"] == "unavailable"
    assert result["error"]["code"] == "sensor_unavailable"


def test_task_target_selection_excludes_support_surfaces_and_rejects_ambiguity():
    green = {"entity_ref": "entity://a2", "category": "green cube"}
    understanding = {"entities": [green, {"entity_ref": "entity://a4", "category": "desktop surface"}]}
    assert select_grasp_target(understanding, "green cube") == green
    with pytest.raises(RuntimeError, match="exactly one"):
        select_grasp_target(understanding, "red cube")
    understanding["entities"].append({"entity_ref": "entity://a5", "category": "green cube"})
    with pytest.raises(RuntimeError, match="exactly one"):
        select_grasp_target(understanding, "green cube")
