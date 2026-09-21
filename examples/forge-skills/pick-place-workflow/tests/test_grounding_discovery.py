import asyncio
from types import SimpleNamespace

from PhyAgentOS.forge.tool_client import ForgeToolClient

from pick_place_workflow.fake_gateway import FakeGatewayTransport


def test_missing_provider_is_not_ready_and_failure_is_preserved():
    async def run():
        failure = {"status": "unavailable", "motion_authorized": False, "error": {"code": "ambiguous"}}
        for provider in (None, SimpleNamespace(bind=lambda _: failure, target=lambda _: failure)):
            async with ForgeToolClient("http://test", transport=FakeGatewayTransport(
                    object(), grounding_provider=provider)) as client:
                for tool in ("scene.bind", "manipulation.target"):
                    context = await client.get_tool_context(tool)
                    assert context["data"]["ready"] is (provider is not None)
                    result = await client.invoke_query_tool(tool, {})
                    assert result["data"]["status"] == "unavailable"
                    if provider is not None:
                        assert result["data"] == failure
                tools = await client.list_tools()
                assert "manipulation.layout" not in {t["tool_id"] for t in tools["data"]["tools"]}
    asyncio.run(run())


def test_task_goal_is_a_read_only_task_fact_query():
    async def run():
        async with ForgeToolClient(
            "http://test", transport=FakeGatewayTransport(object())
        ) as client:
            spec = await client.get_tool("task.goal")
            context = await client.get_tool_context("task.goal")
            result = await client.invoke_query_tool("task.goal", {})
        assert spec["data"]["semantics"] == "query"
        assert spec["data"]["planning"]["requires_before_plan"] is True
        assert context["data"]["motion_authorized"] is False
        assert result["data"]["geometry_source"] == "benchmark_task_definition"
        assert result["data"]["motion_authorized"] is False

    asyncio.run(run())
