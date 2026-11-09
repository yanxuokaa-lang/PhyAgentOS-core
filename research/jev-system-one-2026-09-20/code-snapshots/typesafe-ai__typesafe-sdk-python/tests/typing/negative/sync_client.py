import httpx2
from tenacity import AsyncRetrying

from typesafe_sdk import TypeSafeClient


def invalid_arguments(client: TypeSafeClient) -> None:
    client.system_one(None, {})  # E: Argument `None` is not assignable to parameter `state`
    TypeSafeClient(api_key="test", retry=AsyncRetrying())  # E: Argument `AsyncRetrying` is not assignable to parameter `retry`
    TypeSafeClient(api_key="test", http_client=httpx2.AsyncClient())  # E: Argument `AsyncClient` is not assignable to parameter `http_client`
    client.system_one("x", {}, retry=AsyncRetrying())  # E: Argument `AsyncRetrying` is not assignable to parameter `retry`
    client.system_one("x", {}, response_model=int)  # E: No matching overload
    client.system_one("x", {}, response_model=object())  # E: No matching overload
