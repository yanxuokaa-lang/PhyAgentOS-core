import asyncio
from types import SimpleNamespace

from PhyAgentOS.forge.tool_client import ForgeToolClient

from pick_place_workflow.fake_gateway import FakeGatewayTransport


def test_layout_requires_explicit_provider_and_preserves_provider_result():
    async def exercise():
        result = {"status": "unavailable", "reason": "ambiguous_entities", "motion_authorized": False}
        seen = []

        def invoke(arguments):
            seen.append(arguments)
            return result

        for provider in (None, SimpleNamespace(invoke=invoke)):
            transport = FakeGatewayTransport(object(), layout_provider=provider)
            async with ForgeToolClient("http://fake", transport=transport) as client:
                context = await client.get_tool_context("manipulation.layout")
                assert context["data"]["ready"] is (provider is not None)
                response = await client.invoke_query_tool("manipulation.layout", {"axis": "world+x"})
                assert response["data"]["status"] == "unavailable"
                assert response["data"]["motion_authorized"] is False
                if provider is not None:
                    assert response["data"] == result
        assert seen == [{"axis": "world+x"}]

    asyncio.run(exercise())
