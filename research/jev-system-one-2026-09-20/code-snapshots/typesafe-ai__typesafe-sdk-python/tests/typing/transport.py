import httpx2
from tenacity import AsyncRetrying, Retrying
from typing_extensions import assert_type

from typesafe_sdk import AsyncTypeSafeClient, ListModelsResponse, Noul, SystemOneResponse, TypeSafeClient
from typesafe_sdk._core.config import Config
from typesafe_sdk._core.endpoints import prepare_models, prepare_system_one
from typesafe_sdk._core.transport import Request, RequestState, send, send_async


def sync(config: Config, client: TypeSafeClient, http_client: httpx2.Client, retry: Retrying, response: httpx2.Response) -> None:
    models = prepare_models(config, None, None)
    system_one = prepare_system_one(config, "x", {"q": Noul(instructions="?")}, None, None, None, None, SystemOneResponse)
    assert_type(models, Request[ListModelsResponse])
    assert_type(system_one, Request[SystemOneResponse])
    assert_type(RequestState(models).parse(response), ListModelsResponse)
    assert_type(RequestState(system_one).parse(response), SystemOneResponse)
    assert_type(send(http_client, retry, models), ListModelsResponse)
    assert_type(send(http_client, retry, system_one), SystemOneResponse)
    assert_type(client._request(models), ListModelsResponse)
    assert_type(client._request(system_one), SystemOneResponse)


async def asynchronous(config: Config, client: AsyncTypeSafeClient, http_client: httpx2.AsyncClient, retry: AsyncRetrying) -> None:
    models = prepare_models(config, None, None)
    system_one = prepare_system_one(config, "x", {"q": Noul(instructions="?")}, None, None, None, None, SystemOneResponse)
    assert_type(await send_async(http_client, retry, models), ListModelsResponse)
    assert_type(await send_async(http_client, retry, system_one), SystemOneResponse)
    assert_type(await client._request(models), ListModelsResponse)
    assert_type(await client._request(system_one), SystemOneResponse)
