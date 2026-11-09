from typing import TypeVar

from pydantic import BaseModel
from typing_extensions import assert_type

from tests.test_pydantic_response_models import KnownResponse, TypedSystemOneResponse
from typesafe_sdk import AsyncTypeSafeClient, ChoiceAnswer, Noul, NoulAnswer, ScoreAnswer, SystemOneResponse, TypeSafeClient

PydanticT = TypeVar("PydanticT", bound=BaseModel)


def sync(client: TypeSafeClient, response_model: type[KnownResponse] | None) -> None:
    questions = {"spam": Noul()}
    assert_type(client.system_one("x", questions), SystemOneResponse)
    assert_type(client.system_one("x", questions, response_model=None), SystemOneResponse)
    assert_type(client.system_one("x", questions, response_model=SystemOneResponse), SystemOneResponse)
    assert_type(client.system_one("x", questions, response_model=response_model), KnownResponse | SystemOneResponse)
    standalone = client.system_one("x", questions, response_model=KnownResponse)
    assert_type(standalone, KnownResponse)
    assert_type(standalone.answers.spam, NoulAnswer)
    typed = client.system_one("x", {"spam": Noul()}, response_model=TypedSystemOneResponse)
    assert_type(typed, TypedSystemOneResponse)
    assert_type(typed.spam, NoulAnswer)
    assert_type(typed.nouls, dict[str, NoulAnswer])
    assert_type(typed.choices, dict[str, ChoiceAnswer])
    assert_type(typed.scores, dict[str, ScoreAnswer])


async def asynchronous(client: AsyncTypeSafeClient, response_model: type[KnownResponse] | None) -> None:
    questions = {"spam": Noul()}
    assert_type(await client.system_one("x", questions), SystemOneResponse)
    assert_type(await client.system_one("x", questions, response_model=None), SystemOneResponse)
    assert_type(await client.system_one("x", questions, response_model=SystemOneResponse), SystemOneResponse)
    assert_type(await client.system_one("x", questions, response_model=response_model), KnownResponse | SystemOneResponse)
    standalone = await client.system_one("x", questions, response_model=KnownResponse)
    assert_type(standalone, KnownResponse)
    assert_type(standalone.answers.spam, NoulAnswer)
    typed = await client.system_one("x", {"spam": Noul()}, response_model=TypedSystemOneResponse)
    assert_type(typed, TypedSystemOneResponse)
    assert_type(typed.spam, NoulAnswer)
    assert_type(typed.nouls, dict[str, NoulAnswer])
    assert_type(typed.choices, dict[str, ChoiceAnswer])
    assert_type(typed.scores, dict[str, ScoreAnswer])


def generic_sync(client: TypeSafeClient, response_model: type[PydanticT]) -> PydanticT:
    return client.system_one("x", {"spam": Noul()}, response_model=response_model)


async def generic_async(client: AsyncTypeSafeClient, response_model: type[PydanticT]) -> PydanticT:
    return await client.system_one("x", {"spam": Noul()}, response_model=response_model)
