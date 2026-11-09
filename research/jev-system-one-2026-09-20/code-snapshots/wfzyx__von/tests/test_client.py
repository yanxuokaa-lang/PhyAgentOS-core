import pytest
from von.client import VonClient, AsyncVonClient
from von.types import choice, noul, score


def test_von_client_local():
    client = VonClient(local=True)
    res = client.system_one(
        state="Customer requested cancellation of their monthly plan.",
        questions={
            "action": choice("What does the customer want?", {
                "cancel": "Cancel membership or subscription",
                "upgrade": "Upgrade to a higher tier",
                "support": "Help with usage",
            }),
            "is_cancel": noul("Does the user want to cancel?"),
        },
    )
    assert res.model == "von-1.0.0"
    assert res.answers["action"].choice == "cancel"
    assert res.answers["is_cancel"].noul > 0.5


@pytest.mark.anyio
async def test_async_von_client_local():
    client = AsyncVonClient(local=True)
    res = await client.system_one(
        state="Error: Connection refused on port 5432.",
        questions={
            "service": choice("Which service is failing?", {
                "database": "Database server or Postgres port 5432",
                "web": "Web server or HTTP port",
            }),
        },
    )
    assert res.answers["service"].choice == "database"
