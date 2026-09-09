import httpx
import pytest
from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeError
from PhyAgentOS.forge.capability_runtime.http_transport import CapabilityRuntimeTransport
from test_generic_capability_runtime import ACTION_SPEC, QUERY_SPEC, Action, Query


def test_discovery_and_admission_share_current_readiness():
    state = {"ready": False, "binding_error": "provider starting"}
    runtime = CapabilityRuntime()
    runtime.register_tool(QUERY_SPEC, Query(), context_provider=lambda: dict(state))
    assert runtime.get_context("scene.observe")["ready"] is False
    with pytest.raises(CapabilityRuntimeError, match="starting"):
        runtime.invoke_query("scene_observation", "observe")
    state.update(ready=True, binding_error=None)
    assert runtime.invoke_query("scene_observation", "observe")["status"] == "available"
    state.update(ready=False, binding_error="provider disconnected")
    assert runtime.get_context("scene.observe")["binding_error"] == "provider disconnected"
    with pytest.raises(CapabilityRuntimeError, match="disconnected"):
        runtime.invoke_query("scene_observation", "observe")


@pytest.mark.parametrize("invalid", [None, {}, {"ready": "true"}])
def test_missing_explicit_readiness_never_falls_back_to_static_true(invalid):
    runtime = CapabilityRuntime()
    runtime.register_tool(QUERY_SPEC, Query(), context_provider=lambda: invalid)
    assert runtime.get_context("scene.observe")["ready"] is False
    with pytest.raises(CapabilityRuntimeError, match="context_provider_error"):
        runtime.invoke_query("scene_observation", "observe")


def test_context_failure_blocks_new_action_but_preserves_cancel_and_poll():
    available = True

    def context():
        if not available:
            raise RuntimeError("private endpoint detail")
        return {"ready": True}

    runtime = CapabilityRuntime()
    runtime.register_tool(ACTION_SPEC, Action(pending_polls=5), context_provider=context)
    invocation = runtime.start_action("object.acquire", {})["invocation_id"]
    available = False
    result = runtime.get_context("object.acquire")
    assert result["binding_error"] == "context_provider_error:RuntimeError"
    with pytest.raises(CapabilityRuntimeError, match="context_provider_error"):
        runtime.start_action("object.acquire", {})
    assert runtime.invocation_status(invocation)["status"] == "running"
    assert runtime.cancel_invocation(invocation)["accepted"] is True


@pytest.mark.asyncio
async def test_gateway_context_and_query_routes_reflect_provider_loss():
    state = {"ready": True}
    runtime = CapabilityRuntime()
    runtime.register_tool(QUERY_SPEC, Query(), context_provider=lambda: state)
    async with httpx.AsyncClient(transport=CapabilityRuntimeTransport(runtime), base_url="http://gateway") as client:
        assert (await client.get("/tools/scene.observe/context")).json()["data"]["ready"] is True
        state.update(ready=False, binding_error="sensor unavailable")
        assert (await client.get("/tools/scene.observe/context")).json()["data"]["ready"] is False
        response = await client.post("/tools/scene_observation/observe:invoke", json={"arguments": {}})
        assert response.status_code == 409
        assert "sensor unavailable" in response.json()["error"]["message"]
