from __future__ import annotations

import asyncio
import threading
import time

import pytest

from PhyAgentOS.forge.capability_runtime import (
    ActionAdmission,
    CapabilityRuntime,
    CapabilityRuntimeError,
    CapabilityRuntimeTransport,
    UnknownToolError,
)
from PhyAgentOS.forge.tool_client import ForgeToolClient

QUERY = {
    "tool_id": "scene.observe",
    "endpoint_id": "scene",
    "operation": "observe",
    "semantics": "query",
}
ACTION = {
    "tool_id": "object.acquire",
    "endpoint_id": "object",
    "operation": "acquire",
    "semantics": "action",
}
SESSION = {
    "tool_id": "workflow.session",
    "endpoint_id": "workflow",
    "operation": "run",
    "semantics": "session",
}


class Query:
    def invoke(self, arguments):
        return {"status": "available", "echo": arguments}


class Action:
    def __init__(self, pending_polls=1):
        self.pending_polls = pending_polls

    def admit(self, arguments):
        return ActionAdmission(
            pending_polls=self.pending_polls,
            terminal_result={"status": "succeeded", "world_change_started": False, "arguments": dict(arguments)},
        )


class DeferredAction:
    def __init__(self, runtime):
        self.runtime = runtime
        self.started_with = None

    def admit(self, arguments):
        def start(invocation_id, attempt_id):
            self.started_with = (invocation_id, attempt_id)
            assert invocation_id in self.runtime._invocations
            return ActionAdmission(
                terminal_result={
                    "status": "succeeded",
                    "invocation_id": invocation_id,
                    "attempt_id": attempt_id,
                }
            )

        return ActionAdmission(start=start)


class FailingDeferredAction:
    def admit(self, arguments):
        def start(invocation_id, attempt_id):
            raise RuntimeError("simulated provider start failure")

        return ActionAdmission(start=start)


class MalformedDeferredAction:
    def admit(self, arguments):
        return ActionAdmission(start=lambda invocation_id, attempt_id: {"status": "succeeded"})


@pytest.mark.asyncio
async def test_http_discovery_query_identity_and_action_lifecycle_are_no_motion():
    runtime = CapabilityRuntime()
    runtime.register_tool(QUERY, Query(), context={"ready": True, "motion_authorized": False})
    runtime.register_tool(ACTION, Action(pending_polls=1), context={"max_concurrency": 1, "motion_authorized": False})
    transport = CapabilityRuntimeTransport(runtime, gateway_identity="gateway-conformance")
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        tools = await client.list_tools()
        assert tools["data"]["gateway_identity"] == "gateway-conformance"
        context = await client.get_tool_context("object.acquire")
        assert context["data"]["motion_authorized"] is False
        query = await client.invoke_query("scene", "observe", {"sensor": "front"})
        assert query["data"]["status"] == "available"
        accepted = await client.invoke_action("object.acquire", {"candidate": "c"}, caller_id="paos:t")
        invocation_id = accepted["data"]["invocation_id"]
        status = await client.invocation_status(invocation_id)
        assert status["data"]["caller_id"] == "paos:t"
        result = await client.invocation_result(invocation_id)
        assert result["data"]["status"] == "succeeded"
    assert all(request.method != "POST" or ":invoke" in request.url.path for request in transport.requests)


@pytest.mark.asyncio
async def test_deferred_action_starts_after_invocation_identity_is_allocated():
    runtime = CapabilityRuntime()
    action = DeferredAction(runtime)
    runtime.register_tool(ACTION, action)
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        accepted = await client.invoke_action("object.acquire", {})
        invocation_id = accepted["data"]["invocation_id"]
        assert action.started_with is not None
        assert action.started_with[0] == invocation_id
        result = await client.invocation_result(invocation_id)
        assert result["data"]["status"] == "succeeded"
        assert result["data"]["result"]["attempt_id"] == action.started_with[1]


@pytest.mark.asyncio
async def test_deferred_action_start_failure_is_terminal_failure_with_identity():
    runtime = CapabilityRuntime()
    runtime.register_tool(ACTION, FailingDeferredAction())
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        accepted = await client.invoke_action("object.acquire", {})
        invocation_id = accepted["data"]["invocation_id"]
        result = await client.invocation_result(invocation_id)
        assert result["data"]["status"] == "failed"
        assert result["data"]["result"]["failure_code"] == "action_start_failed"


@pytest.mark.asyncio
async def test_malformed_deferred_start_leaves_a_queryable_failed_invocation():
    runtime = CapabilityRuntime()
    runtime.register_tool(ACTION, MalformedDeferredAction())
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        with pytest.raises(Exception):
            await client.invoke_action("object.acquire", {})
        assert len(runtime._invocations) == 1
        invocation_id = next(iter(runtime._invocations))
        result = await client.invocation_result(invocation_id)
        assert result["data"]["status"] == "failed"
        assert result["data"]["result"]["failure_code"] == "invalid_action_start_result"


@pytest.mark.asyncio
async def test_timeout_unknown_recovery_does_not_post_again():
    now = [10.0]
    runtime = CapabilityRuntime(clock=lambda: now[0])
    runtime.register_tool(ACTION, Action(pending_polls=10))
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        accepted = await client.invoke_action("object.acquire", {}, timeout_ms=1000)
        invocation_id = accepted["data"]["invocation_id"]
        now[0] = 11.0
        result = await client.invocation_result(invocation_id)
        assert result["data"]["status"] == "unknown"
        post_count = len([request for request in transport.requests if request.method == "POST"])
        again = await client.invocation_result(invocation_id)
        assert again["data"]["status"] == "unknown"
        assert len([request for request in transport.requests if request.method == "POST"]) == post_count
    invoke_posts = [request for request in transport.requests if request.method == "POST" and request.url.path.endswith(":invoke")]
    assert len(invoke_posts) == 1


@pytest.mark.asyncio
async def test_cancel_and_session_stop_reconcile_to_terminal_states():
    runtime = CapabilityRuntime()
    runtime.register_tool(ACTION, Action(pending_polls=3))
    runtime.register_tool(SESSION, Action(pending_polls=3))
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        action = await client.invoke_action("object.acquire", {})
        action_id = action["data"]["invocation_id"]
        await client.cancel_invocation(action_id)
        assert (await client.invocation_result(action_id))["data"]["status"] == "cancelled"
        session = await client.start_session("workflow.session", {})
        session_id = session["data"]["invocation_id"]
        await client.stop_session(session_id)
        assert (await client.invocation_result(session_id))["data"]["status"] == "stopped"


@pytest.mark.asyncio
async def test_malformed_invoke_payload_is_a_client_error_and_does_not_admit():
    runtime = CapabilityRuntime()
    runtime.register_tool(ACTION, Action())
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        request = client._client.build_request("POST", "/tools/object.acquire:invoke", content=b"{")
        response = await client._client.send(request)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_json"
    assert not runtime._invocations


class BlockingStatusRuntime:
    """Fake runtime whose ``invocation_status`` blocks the calling thread."""

    def __init__(self):
        self.entered = threading.Event()

    def invocation_status(self, invocation_id):
        self.entered.set()
        time.sleep(0.3)  # stands in for a multi-minute synchronous driver step
        return {"invocation_id": invocation_id, "status": "running"}


class RecordingInvokeRuntime:
    """Fake runtime recording synchronous ``start_action`` enter/exit order."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counter = 0
        self.timeline = []

    def _record(self, event):
        with self._lock:
            self.timeline.append(event)

    def start_action(self, tool_id, arguments, caller_id=None, timeout_ms=None):
        self._record(("enter", tool_id))
        time.sleep(0.05)
        self._record(("exit", tool_id))
        with self._lock:
            self._counter += 1
            invocation_id = f"inv-{self._counter}"
        return {"invocation_id": invocation_id, "status": "succeeded"}


class FailingInvokeRuntime:
    """Fake runtime raising the runtime's own error classes from its calls."""

    def invoke_query(self, endpoint_id, operation, arguments):
        if operation == "missing":
            raise UnknownToolError(f"operation {operation!r} is not registered")
        raise CapabilityRuntimeError(f"endpoint {endpoint_id!r} failed to dispatch")


async def _loop_stays_responsive_while_runtime_call_blocks():
    runtime = BlockingStatusRuntime()
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        pending = asyncio.create_task(client.invocation_status("inv-1"))
        loop = asyncio.get_running_loop()
        assert await loop.run_in_executor(None, runtime.entered.wait, 2.0), "runtime call never started"
        heartbeat_start = loop.time()
        await asyncio.wait_for(asyncio.sleep(0.05), timeout=1)
        heartbeat_elapsed = loop.time() - heartbeat_start
        assert not pending.done(), "runtime call finished before the heartbeat; test window missed"
        assert heartbeat_elapsed < 0.25, "event loop stayed blocked during the runtime call"
        data = await pending
        assert data["data"]["status"] == "running"


async def _concurrent_invokes_do_not_interleave():
    runtime = RecordingInvokeRuntime()
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        first, second = await asyncio.gather(
            client.invoke_action("object.acquire", {"n": 1}),
            client.invoke_action("object.acquire", {"n": 2}),
        )
        assert first["data"]["invocation_id"] != second["data"]["invocation_id"]
    assert [event[:2] for event in runtime.timeline] == [
        ("enter", "object.acquire"),
        ("exit", "object.acquire"),
        ("enter", "object.acquire"),
        ("exit", "object.acquire"),
    ]


async def _runtime_errors_raised_in_worker_map_to_http_errors():
    runtime = FailingInvokeRuntime()
    transport = CapabilityRuntimeTransport(runtime)
    async with ForgeToolClient("http://runtime", transport=transport) as client:
        request = client._client.build_request("POST", "/tools/scene/observe:invoke", json={"arguments": {}})
        response = await client._client.send(request)
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "runtime_error"
        assert body["error"]["message"] == "endpoint 'scene' failed to dispatch"
        missing = client._client.build_request("POST", "/tools/scene/missing:invoke", json={"arguments": {}})
        response = await client._client.send(missing)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


# Plain asyncio.run wrappers so these run even with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
# (the coverage env where pytest-asyncio is not loaded).
def test_transport_keeps_event_loop_responsive_while_runtime_call_blocks():
    asyncio.run(_loop_stays_responsive_while_runtime_call_blocks())


def test_transport_serializes_concurrent_runtime_calls():
    asyncio.run(_concurrent_invokes_do_not_interleave())


def test_transport_maps_worker_raised_runtime_errors_to_http_errors():
    asyncio.run(_runtime_errors_raised_in_worker_map_to_http_errors())
