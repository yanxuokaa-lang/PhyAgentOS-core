import httpx2
from tenacity import Retrying

from typesafe_sdk import AsyncTypeSafeClient


async def invalid_arguments(client: AsyncTypeSafeClient) -> None:
    await client.system_one(None, {})  # E: Argument `None` is not assignable to parameter `state`
    AsyncTypeSafeClient(api_key="test", retry=Retrying())  # E: Argument `Retrying` is not assignable to parameter `retry`
    AsyncTypeSafeClient(api_key="test", http_client=httpx2.Client())  # E: Argument `Client` is not assignable to parameter `http_client`
    await client.system_one("x", {}, retry=Retrying())  # E: Argument `Retrying` is not assignable to parameter `retry`
    await client.system_one("x", {}, response_model=int)  # E: No matching overload
    await client.system_one("x", {}, response_model=object())  # E: No matching overload
