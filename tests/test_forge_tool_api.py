from __future__ import annotations

import asyncio
import json

from PhyAgentOS.agent.tools.forge_tool_api import _call, _effective_query_timeout_ms
from PhyAgentOS.forge.tool_client import ForgeToolAPITimeoutError


def test_scene_understand_timeout_has_provider_safe_floor():
    assert _effective_query_timeout_ms("scene.understand", None) == 180_000
    assert _effective_query_timeout_ms("scene.understand", 30_000) == 180_000
    assert _effective_query_timeout_ms("scene.understand", 240_000) == 240_000


def test_other_query_timeouts_are_not_changed():
    assert _effective_query_timeout_ms("scene.observe", None) is None
    assert _effective_query_timeout_ms("scene.observe", 30_000) == 30_000


def test_timeout_response_is_explicit_and_reasoned():
    async def timed_out():
        raise ForgeToolAPITimeoutError("GET /tools/scene.understand timed out", timeout_s=180.0)

    payload = json.loads(asyncio.run(_call(timed_out)))
    assert payload["ok"] is False
    assert payload["error"]["type"] == "timeout"
    assert payload["error"]["status"] == "timeout"
    assert payload["error"]["code"] == "gateway_timeout"
    assert payload["error"]["remote_state"] == "unconfirmed"
    assert "timeout_budget_s=180" in payload["error"]["reason"]
