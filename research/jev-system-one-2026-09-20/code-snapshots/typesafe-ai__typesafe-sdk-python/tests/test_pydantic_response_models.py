from typing import Literal

import httpx2
import pytest
from pydantic import BaseModel, ConfigDict

from tests.conftest import ClientFactory
from tests.test_clients import RESULT
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Noul,
    NoulAnswer,
    SystemOneResponse,
    TypeSafeAPIResponseValidationError,
    TypeSafeBadRequestError,
)


class KnownAnswers(BaseModel):
    spam: NoulAnswer


class KnownResponse(BaseModel):
    model: str
    answers: KnownAnswers


class ToneProbabilities(BaseModel):
    friendly: float
    hostile: float


class Tone(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    choice: Literal["friendly", "hostile"]
    probabilities: ToneProbabilities


class TypedSystemOneResponse(SystemOneResponse):
    spam: NoulAnswer
    tone: Tone
    missing: NoulAnswer | None = None


@pytest.mark.parametrize("extra_answer_fields", [{}, {"explanation": "spammy"}])
async def test_standalone_pydantic_response_model(clients: ClientFactory, extra_answer_fields: dict[str, str]) -> None:
    body = {**RESULT, "answers": {**RESULT["answers"], "spam": {**RESULT["answers"]["spam"], **extra_answer_fields}}}
    client = clients(lambda request: httpx2.Response(200, json=body))
    if isinstance(client, AsyncTypeSafeClient):
        result = await client.system_one("x", {"spam": Noul()}, response_model=KnownResponse)
    else:
        result = client.system_one("x", {"spam": Noul()}, response_model=KnownResponse)
    assert type(result) is KnownResponse
    assert result.model == "jev-latest"
    assert result.answers.spam.noul == 0.98


@pytest.mark.parametrize("response_model", [None, SystemOneResponse])
async def test_explicit_default_response_model(clients: ClientFactory, response_model: type[SystemOneResponse] | None) -> None:
    client = clients(lambda request: httpx2.Response(200, json=RESULT, headers={"x-typesafe-request-id": "req-default"}))
    if isinstance(client, AsyncTypeSafeClient):
        result = await client.system_one("x", {"spam": Noul()}, response_model=response_model)
    else:
        result = client.system_one("x", {"spam": Noul()}, response_model=response_model)
    assert isinstance(result, SystemOneResponse)
    assert result.nouls["spam"].noul == 0.98
    assert result.request_id == "req-default"
    assert result.raw_http_response.json() == RESULT


async def test_pydantic_system_one_response_subclass(clients: ClientFactory) -> None:
    body = {**RESULT, "answers": {**RESULT["answers"], "future": {"type": "future", "value": 1}}}
    client = clients(lambda request: httpx2.Response(200, json=body, headers={"x-typesafe-request-id": "req-pydantic"}))
    if isinstance(client, AsyncTypeSafeClient):
        result = await client.system_one("x", {"spam": Noul()}, response_model=TypedSystemOneResponse)
    else:
        result = client.system_one("x", {"spam": Noul()}, response_model=TypedSystemOneResponse)
    assert type(result) is TypedSystemOneResponse
    assert result.spam.noul == 0.98
    assert result.tone.choice == "friendly"
    assert result.tone.probabilities.friendly == 0.9
    assert result.missing is None
    assert result.nouls["spam"].noul == 0.98
    assert result.choices["tone"].choice == "friendly"
    assert result.scores["quality"].score == 1.7
    assert "future" not in result.answers
    assert result.request_id == "req-pydantic"
    assert result.raw_http_response.json() == body
    assert "_raw" not in result.model_dump()
    assert "_request_id" not in result.model_dump()


@pytest.mark.parametrize(
    "response_model,body,field_path",
    [
        (KnownResponse, {"model": "test", "answers": {"spam": {"type": "noul"}}}, "answers.spam.noul"),
        (
            TypedSystemOneResponse,
            {**RESULT, "answers": {**RESULT["answers"], "tone": {**RESULT["answers"]["tone"], "choice": "unknown"}}},
            "tone.choice",
        ),
    ],
)
async def test_pydantic_response_validation(
    clients: ClientFactory, response_model: type[BaseModel], body: dict[str, object], field_path: str
) -> None:
    client = clients(lambda request: httpx2.Response(200, json=body, headers={"x-typesafe-request-id": "req-invalid"}))
    if isinstance(client, AsyncTypeSafeClient):
        with pytest.raises(TypeSafeAPIResponseValidationError) as caught:
            await client.system_one("x", {"spam": Noul()}, response_model=response_model)
    else:
        with pytest.raises(TypeSafeAPIResponseValidationError) as caught:
            client.system_one("x", {"spam": Noul()}, response_model=response_model)
    assert caught.value.field_path == field_path
    assert caught.value.request_id == "req-invalid"
    assert caught.value.body == body


async def test_custom_response_preserves_api_errors(clients: ClientFactory) -> None:
    body = {"detail": "Invalid request"}
    client = clients(lambda request: httpx2.Response(400, json=body, headers={"x-typesafe-request-id": "req-error"}))
    if isinstance(client, AsyncTypeSafeClient):
        with pytest.raises(TypeSafeBadRequestError) as caught:
            await client.system_one("x", {"spam": Noul()}, response_model=KnownResponse)
    else:
        with pytest.raises(TypeSafeBadRequestError) as caught:
            client.system_one("x", {"spam": Noul()}, response_model=KnownResponse)
    assert caught.value.status == 400
    assert caught.value.body == body
    assert caught.value.request_id == "req-error"
