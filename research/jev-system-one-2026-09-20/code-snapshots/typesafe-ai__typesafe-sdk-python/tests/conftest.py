import os
from collections.abc import AsyncIterator, Callable, Mapping

import httpx2
import pytest

from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeClient
from typesafe_sdk.constants import API_KEY_ENV, BASE_URL_ENV, DEFAULT_MODEL_ENV, LOG_LEVEL_ENV

Client = TypeSafeClient | AsyncTypeSafeClient


class ClientFactory:
    def __init__(self, async_mode: bool) -> None:
        self.async_mode = async_mode
        self.instances: list[Client] = []

    def __call__(
        self,
        handler: Callable[[httpx2.Request], httpx2.Response],
        *,
        retries: bool = False,
        api_key: str | None = "test-key",
        model: str | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | httpx2.Timeout | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx2.BaseTransport | httpx2.AsyncBaseTransport | None = None,
        http_client: httpx2.Client | httpx2.AsyncClient | None = None,
        base_url: str | None = None,
    ) -> Client:
        if transport is None and http_client is None:
            transport = httpx2.MockTransport(handler)
        if retry is None and not retries:
            retry = RetryPolicy(max_retries=0)
        client: Client
        if self.async_mode:
            assert transport is None or isinstance(transport, httpx2.AsyncBaseTransport)
            assert http_client is None or isinstance(http_client, httpx2.AsyncClient)
            client = AsyncTypeSafeClient(
                api_key=api_key,
                model=model,
                retry=retry,
                timeout=timeout,
                headers=headers,
                transport=transport,
                http_client=http_client,
                base_url=base_url,
            )
        else:
            assert transport is None or isinstance(transport, httpx2.BaseTransport)
            assert http_client is None or isinstance(http_client, httpx2.Client)
            client = TypeSafeClient(
                api_key=api_key,
                model=model,
                retry=retry,
                timeout=timeout,
                headers=headers,
                transport=transport,
                http_client=http_client,
                base_url=base_url,
            )
        self.instances.append(client)
        return client


@pytest.fixture(params=[False, True], ids=["sync", "async"])
async def clients(request: pytest.FixtureRequest) -> AsyncIterator[ClientFactory]:
    factory = ClientFactory(request.param)
    yield factory
    for client in factory.instances:
        if isinstance(client, AsyncTypeSafeClient):
            await client.aclose()
        else:
            client.close()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("integration") is None:
        for name in (API_KEY_ENV, BASE_URL_ENV, DEFAULT_MODEL_ENV, LOG_LEVEL_ENV):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def live_api_key() -> str:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        pytest.skip(f"{API_KEY_ENV} is not set")
    return key


@pytest.fixture(params=["sync", "async"])
async def live_client(request: pytest.FixtureRequest, live_api_key: str) -> AsyncIterator[Client]:
    if request.param == "async":
        async with AsyncTypeSafeClient(api_key=live_api_key, timeout=120) as client:
            yield client
    else:
        with TypeSafeClient(api_key=live_api_key, timeout=120) as client:
            yield client
