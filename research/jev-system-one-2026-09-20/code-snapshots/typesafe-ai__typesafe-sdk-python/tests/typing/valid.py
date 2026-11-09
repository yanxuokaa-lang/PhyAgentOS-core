from collections.abc import Mapping
from types import MappingProxyType
from typing import cast

import httpx2
from typing_extensions import assert_type

from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    ChoiceModel,
    ListModelsResponse,
    Questions,
    RetryPolicy,
    Score,
    SystemOneResponse,
    TypeSafeClient,
)


def sync(client: TypeSafeClient) -> None:
    objects: dict[str, Choice] = {"q": Choice(instructions="?", criteria={"a": None})}
    data: dict[str, ChoiceModel] = {"q": {"type": "choice", "instructions": "?", "criteria": {"a": None}}}
    # Abstract inputs: a MappingProxyType with a nested tuple as state, and tuple score criteria.
    state = MappingProxyType({"items": ("a", None)})
    assert_type(client.system_one(state, {"s": Score(criteria=("low", "high"))}), SystemOneResponse)
    assert_type(client.system_one({"nullable": None}, objects, retry=RetryPolicy(), timeout=httpx2.Timeout(None)), SystemOneResponse)
    assert_type(client.system_one("x", data, model="test", extra_headers={"x-call": "test"}), SystemOneResponse)
    future_questions = cast(Questions, {"q": {"type": "noul", "instructions": "?", "weight": 2}})
    assert_type(client.system_one("x", future_questions, retry=RetryPolicy(max_retries=1)), SystemOneResponse)
    assert_type(client.system_one("x", data, extra_body={"beam_width": 4, "nullable": None}), SystemOneResponse)
    assert_type(client.models.list(retry=RetryPolicy(), timeout=2.0, extra_headers={"x-call": "test"}), ListModelsResponse)
    TypeSafeClient(retry=RetryPolicy(max_retries=1))


async def asynchronous(client: AsyncTypeSafeClient) -> None:
    objects: Mapping[str, Choice] = {"q": Choice(instructions="?", criteria={"a": None})}
    data: dict[str, ChoiceModel] = {"q": {"type": "choice", "instructions": "?", "criteria": {"a": None}}}
    assert_type(await client.system_one({"nullable": None}, objects, retry=RetryPolicy(), timeout=2.0), SystemOneResponse)
    assert_type(await client.system_one("x", data, model="test", extra_headers={"x-call": "test"}), SystemOneResponse)
    future_questions = cast(Questions, {"q": {"type": "noul", "instructions": "?", "weight": 2}})
    assert_type(await client.system_one("x", future_questions, retry=RetryPolicy()), SystemOneResponse)
    assert_type(await client.system_one("x", data, extra_body={"beam_width": 4, "nullable": None}), SystemOneResponse)
    assert_type(await client.models.list(retry=RetryPolicy(), timeout=2.0, extra_headers={"x-call": "test"}), ListModelsResponse)
    AsyncTypeSafeClient(retry=RetryPolicy(max_retries=1))
