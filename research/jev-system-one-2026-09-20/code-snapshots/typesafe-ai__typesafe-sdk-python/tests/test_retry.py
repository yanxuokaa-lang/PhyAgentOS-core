import asyncio
from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import httpx2
import pytest
from pydantic_core import from_json, to_json
from tenacity import RetryCallState

from tests.conftest import ClientFactory
from tests.helpers import models, system_one
from tests.test_clients import RESULT
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Noul,
    Questions,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPITimeoutError,
    TypeSafeError,
    TypeSafeRateLimitError,
)
from typesafe_sdk._core.errors import parse_retry_after


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_retry_policy_invalid_timeout(timeout: float) -> None:
    with pytest.raises(TypeSafeError, match="timeout must be a positive, finite number of seconds"):
        RetryPolicy(timeout=timeout)


@pytest.mark.parametrize("initial,maximum", [(0.0, 5.0), (0.5, 0.0), (0.0, 0.0)])
@pytest.mark.parametrize("recover", [False, True])
async def test_zero_backoff_retries(clients: ClientFactory, initial: float, maximum: float, recover: bool) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if recover and len(requests) == 2:
            return httpx2.Response(200, json={"models": []})
        return httpx2.Response(503, json={"message": "temporarily unavailable"})

    client = clients(handler, retry=RetryPolicy(max_retries=1, backoff_initial=initial, backoff_max=maximum))
    if recover:
        assert await models(client) == ()
    else:
        with pytest.raises(TypeSafeAPIError, match="temporarily unavailable"):
            await models(client)
    assert [request.headers.get("x-typesafe-retry-count") for request in requests] == [None, "1"]


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
@pytest.mark.parametrize("field", ["backoff_initial", "backoff_max"])
def test_invalid_backoff(field: str, value: float) -> None:
    with pytest.raises(TypeSafeError, match=field):
        RetryPolicy(backoff_initial=value if field == "backoff_initial" else 0.5, backoff_max=value if field == "backoff_max" else 5.0)


@pytest.mark.parametrize("jitter", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_backoff_jitter(jitter: float) -> None:
    with pytest.raises(TypeSafeError, match="backoff_jitter"):
        RetryPolicy(backoff_jitter=jitter)


@pytest.mark.parametrize("retries", [-1, 0.5, float("nan"), float("inf")])
def test_invalid_max_retries(retries: int) -> None:
    with pytest.raises(TypeSafeError, match="max_retries"):
        RetryPolicy(max_retries=retries)


@pytest.mark.parametrize("resource", ["models", "system_one"])
@pytest.mark.parametrize(
    "timeout,duration,delay,attempts",
    [(None, 1.0, 0.5, 3), (30.0, 10.0, 5.0, 2), (2.5, 0.75, 0.5, 2), (2.0, 1.0, 0.0, 2), (1.0, 0.0, 1.0, 1), (1.0, 0.0, 60.0, 1)],
)
async def test_retry_policy_timeout_budget(
    clients: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
    resource: str,
    timeout: float | None,
    duration: float,
    delay: float,
    attempts: int,
) -> None:
    now = 100.0
    requests: list[httpx2.Request] = []
    delays: list[float] = []
    monkeypatch.setattr("tenacity.time", SimpleNamespace(monotonic=lambda: now))

    def sleep(seconds: float) -> None:
        nonlocal now
        delays.append(seconds)
        now += seconds

    async def sleep_async(seconds: float) -> None:
        sleep(seconds)

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal now
        now += duration
        requests.append(request)
        return httpx2.Response(429, json={"message": f"attempt {len(requests)}"}, headers={"Retry-After": str(delay)})

    client = clients(handler, retry=RetryPolicy(timeout=timeout))
    if isinstance(client, AsyncTypeSafeClient):
        if resource == "models":
            client.models._retry = client.models._retry.copy(sleep=sleep_async)
        else:
            client._retry = client._retry.copy(sleep=sleep_async)
    elif resource == "models":
        client.models._retry = client.models._retry.copy(sleep=sleep)
    else:
        client._retry = client._retry.copy(sleep=sleep)

    async def call() -> None:
        if resource == "models":
            await models(client)
        else:
            await system_one(client, state="x", questions={"q": Noul(instructions="?")})

    for _ in range(2):  # Each SDK call gets a fresh budget.
        requests.clear()
        delays.clear()
        with pytest.raises(TypeSafeRateLimitError, match=f"attempt {attempts}$"):
            await call()
        assert len(requests) == attempts
        assert delays == [delay] * (attempts - 1)


@pytest.mark.parametrize("resource", ["models", "system_one"])
async def test_retry_policy_timeout_override(clients: ClientFactory, monkeypatch: pytest.MonkeyPatch, resource: str) -> None:
    now = 100.0
    attempts = 0
    monkeypatch.setattr("tenacity.time", SimpleNamespace(monotonic=lambda: now))

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal now, attempts
        # Each attempt advances the mock clock by 20s so the default 30.0s budget binds before the
        # third attempt (elapsed 40s >= 30s), rather than only max_retries capping the loop.
        now += 20.0
        attempts += 1
        return httpx2.Response(429, headers={"retry-after-ms": "0"})

    client = clients(handler, retry=RetryPolicy())

    async def call(retry: RetryPolicy | None) -> None:
        if resource == "models":
            await models(client, retry=retry)
        else:
            await system_one(client, state="x", questions={"q": Noul(instructions="?")}, retry=retry)

    for policy, expected in [(None, 2), (RetryPolicy(timeout=1.0), 1), (RetryPolicy(timeout=None), 3), (None, 2)]:
        attempts = 0
        with pytest.raises(TypeSafeRateLimitError):
            await call(policy)
        assert attempts == expected


@pytest.mark.parametrize(
    "status,attempts", [(408, 3), (429, 3), (500, 3), (503, 3), (599, 3), (400, 1), (401, 1), (403, 1), (404, 1), (409, 1), (422, 1), (302, 1)]
)
async def test_default_retry_statuses(clients: ClientFactory, status: int, attempts: int) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(status, json={"message": "failed"}, headers={"retry-after-ms": "0"})

    with pytest.raises(TypeSafeAPIError) as caught:
        await models(clients(handler, retries=True))
    assert caught.value.status == status
    assert len(requests) == attempts
    assert [request.headers.get("x-typesafe-retry-count") for request in requests] == [None, "1", "2"][:attempts]


@pytest.mark.parametrize("kind", [httpx2.ConnectError, httpx2.ReadTimeout, httpx2.ReadError])
async def test_connection_retry_recovers(clients: ClientFactory, kind: type[httpx2.RequestError]) -> None:
    attempts = 0
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise kind("failed", request=request)
        else:
            return httpx2.Response(200, json={"models": []})

    client = clients(handler, retries=True)
    if isinstance(client, AsyncTypeSafeClient):
        client.models._retry = client.models._retry.copy(sleep=sleep)
    else:
        client.models._retry = client.models._retry.copy(sleep=delays.append)
    assert await models(client) == ()
    assert attempts == 3
    assert 0.375 <= delays[0] <= 0.5
    assert 0.75 <= delays[1] <= 1.0


@pytest.mark.parametrize(
    "headers,delay",
    [
        ({"Retry-After": "2"}, 2.0),
        ({"retry-after-ms": "125"}, 0.125),
        ({"retry-after-ms": "0", "Retry-After": "50"}, 0.0),
        ({"Retry-After": "60"}, 60.0),
    ],
)
async def test_server_delay_through_tenacity(clients: ClientFactory, headers: dict[str, str], delay: float) -> None:
    attempts = 0
    delays: list[float] = []

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(429, json={}, headers=headers) if attempts == 1 else httpx2.Response(200, json={"models": []})

    client = clients(handler, retry=RetryPolicy(timeout=None))
    if isinstance(client, AsyncTypeSafeClient):
        client.models._retry = client.models._retry.copy(sleep=sleep)
    else:
        client.models._retry = client.models._retry.copy(sleep=delays.append)
    assert await models(client) == ()
    assert delays == [delay]


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({}, None),
        ({"Retry-After": "bad"}, None),
        ({"Retry-After": "-1"}, None),
        ({"retry-after-ms": "NaN", "Retry-After": "1.5"}, 1500),
        ({"retry-after-ms": "-1", "Retry-After": "2"}, 2000),
        ({"Retry-After": ""}, 0),
        ({"retry-after-ms": "inf"}, None),
        ({"retry-after-ms": "bad", "Retry-After": "2"}, 2000),
        ({"Retry-After": "1e308"}, None),
    ],
)
def test_parse_retry_after(headers: dict[str, str], expected: float | None) -> None:
    assert parse_retry_after(httpx2.Headers(headers)) == expected


def test_backoff_dates_cap_and_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.time", lambda: 1_000_000.0)
    future = format_datetime(datetime.fromtimestamp(1_000_010, timezone.utc), usegmt=True)
    past = format_datetime(datetime.fromtimestamp(999_990, timezone.utc), usegmt=True)
    assert parse_retry_after(httpx2.Headers({"Retry-After": future})) == 10_000
    assert parse_retry_after(httpx2.Headers({"Retry-After": past})) == 0
    wait = RetryPolicy()._wait
    state = RetryCallState(RetryPolicy()._build_tenacity(), None, (), {})
    monkeypatch.setattr("random.random", lambda: 0.0)
    for attempt, expected in [(1, 0.5), (2, 1.0), (3, 2.0), (4, 4.0), (5, 5.0), (20, 5.0)]:
        state.attempt_number = attempt
        assert wait(state) == expected
    monkeypatch.setattr("random.random", lambda: 1.0)
    state.attempt_number = 1
    assert wait(state) == 0.375
    for header, expected in [({"Retry-After": "61"}, 61), ({"retry-after-ms": "60001"}, 60.001), ({"Retry-After": future}, 10)]:
        error = TypeSafeRateLimitError(429, {}, httpx2.Headers(header))
        state.set_exception((type(error), error, None))
        assert wait(state) == expected  # Server-requested delays are always honored, however long.
    error = TypeSafeRateLimitError(429, {}, httpx2.Headers({"Retry-After": "bad"}))  # Unparseable headers fall back to backoff.
    state.set_exception((type(error), error, None))
    assert wait(state) == 0.375


@pytest.mark.parametrize("client_attempts,call_attempts", [(1, 3), (3, 1)])
async def test_system_one_retry_override(clients: ClientFactory, client_attempts: int, call_attempts: int) -> None:
    requests: list[httpx2.Request] = []
    client_policy = RetryPolicy(max_retries=client_attempts - 1)
    call_policy = RetryPolicy(max_retries=call_attempts - 1, http_statuses={409})

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        status = 409 if request.headers["x-call"] == "override" else 429
        return httpx2.Response(status, json={"message": "failed"}, headers={"retry-after-ms": "0"})

    client = clients(handler, retry=client_policy)
    calls = [
        ("override", call_policy, call_attempts),
        ("inherited", None, client_attempts),
        ("override", call_policy, call_attempts),
    ]
    for name, retry, attempts in calls:
        requests.clear()
        with pytest.raises(TypeSafeAPIError):
            await system_one(
                client,
                state="hello",
                questions={"q": {"type": "noul", "instructions": "?"}},
                extra_headers={"x-call": name},
                retry=retry,
            )
        assert [request.headers.get("x-typesafe-retry-count") for request in requests] == [None, *(str(index) for index in range(1, attempts))]


async def test_async_concurrent_retry_state() -> None:
    attempts: dict[str, list[str | None]] = {}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        key = request.headers["x-call"]
        calls = attempts.setdefault(key, [])
        calls.append(request.headers.get("x-typesafe-retry-count"))
        await asyncio.sleep(0)
        return httpx2.Response(429, headers={"retry-after-ms": "0"}) if len(calls) == 1 else httpx2.Response(200, json={"models": []})

    async with AsyncTypeSafeClient(api_key="test", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))) as client:
        responses = await asyncio.gather(*(client.models.list(extra_headers={"x-call": str(index)}) for index in range(4)))
        assert [response.models for response in responses] == [(), (), (), ()]
    assert all(value == [None, "1"] for value in attempts.values())


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("timeout", [2.0, httpx2.Timeout(3.0, connect=1.0, read=5.0)])
async def test_system_one_retry_recovers_with_overrides(
    clients: ClientFactory,
    raw: bool,
    timeout: float | httpx2.Timeout,
) -> None:
    requests: list[httpx2.Request] = []
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    questions: Questions = {
        "q": {"type": "noul", "instructions": "?"} if raw else Noul(instructions="?"),
    }

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if len(requests) == 1:
            raise httpx2.ReadTimeout("timed out", request=request)
        elif len(requests) == 2:
            return httpx2.Response(429, json={"message": "slow down"}, headers={"retry-after-ms": "125"})
        return httpx2.Response(200, json=RESULT)

    headers = {"x-call": "override", "authorization": "must-not-win"}
    client = clients(handler, model="client-model", timeout=7.0, headers={"x-default": "kept"}, retries=True)
    if isinstance(client, AsyncTypeSafeClient):
        client._retry = client._retry.copy(sleep=sleep)
    else:
        client._retry = client._retry.copy(sleep=delays.append)
    result = await system_one(
        client,
        state={"document": "hello"},
        questions=questions,
        model="call-model",
        timeout=timeout,
        extra_headers=headers,
    )
    assert result.scores["quality"].score == 1.7
    assert result.choices["tone"].confidence == 0.9
    expected = to_json(
        {
            "state": {"document": "hello"},
            "model": "call-model",
            "questions": {"q": {"type": "noul", "instructions": "?"}},
        }
    )
    for request in requests:
        assert request.content == expected
        assert request.extensions["timeout"] == httpx2.Timeout(timeout).as_dict()
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.headers["x-default"] == "kept"
        assert request.headers["x-call"] == "override"
    assert [request.headers.get("x-typesafe-retry-count") for request in requests] == [None, "1", "2"]
    assert 0.375 <= delays[0] <= 0.5
    assert delays[1] == 0.125
    assert headers == {"x-call": "override", "authorization": "must-not-win"}

    await system_one(client, state="next", questions=questions)
    assert from_json(requests[-1].content)["model"] == "client-model"
    assert requests[-1].extensions["timeout"] == httpx2.Timeout(7.0).as_dict()
    assert "x-call" not in requests[-1].headers
    assert "x-typesafe-retry-count" not in requests[-1].headers


async def test_concurrent_system_one_overrides() -> None:
    attempts: dict[str, list[httpx2.Request]] = {}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        key = request.headers["x-call"]
        calls = attempts.setdefault(key, [])
        calls.append(request)
        await asyncio.sleep(0)
        return httpx2.Response(429, json={"message": "retry"}, headers={"retry-after-ms": "0"})

    async with AsyncTypeSafeClient(
        api_key="test",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        retry=RetryPolicy(max_retries=1),
        timeout=9.0,
    ) as client:

        async def call(name: str, retries: int | None, timeout: float) -> None:
            with pytest.raises(TypeSafeRateLimitError):
                await client.system_one(
                    state=name,
                    questions={"q": Noul(instructions="?")},
                    model=name,
                    extra_headers={"x-call": name},
                    timeout=timeout,
                    retry=None if retries is None else RetryPolicy(max_retries=retries - 1),
                )

        await asyncio.gather(call("one", 1, 1.0), call("three", 3, 3.0), call("default", None, 2.0))
    for name, count in (("one", 1), ("three", 3), ("default", 2)):
        requests = attempts[name]
        assert len(requests) == count
        assert [request.headers.get("x-typesafe-retry-count") for request in requests] == [
            None,
            *(str(index) for index in range(1, count)),
        ]
        assert all(from_json(request.content)["model"] == name for request in requests)
        assert all(from_json(request.content)["state"] == name for request in requests)
        assert all(request.extensions["timeout"] == httpx2.Timeout(float(count)).as_dict() for request in requests)


@pytest.mark.parametrize("kind", [httpx2.ReadTimeout, httpx2.ConnectError])
async def test_exhausted_transport_retry(clients: ClientFactory, kind: type[httpx2.RequestError]) -> None:
    attempts = 0
    timeout = httpx2.Timeout(2.0, read=4.0)

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        raise kind(f"attempt {attempts}", request=request)

    with pytest.raises(TypeSafeAPIConnectionError) as caught:
        await system_one(
            clients(handler),
            state="x",
            questions={"q": Noul(instructions="?")},
            retry=RetryPolicy(backoff_initial=0.001, backoff_max=0.001),
            timeout=timeout,
        )
    assert attempts == 3
    assert isinstance(caught.value.__cause__, kind)
    assert str(caught.value.__cause__) == "attempt 3"
    if kind is httpx2.ReadTimeout:
        assert isinstance(caught.value, TypeSafeAPITimeoutError)
        assert caught.value.timeout is timeout
    else:
        assert type(caught.value) is TypeSafeAPIConnectionError


async def test_exhausted_retry_preserves_final_http_error(clients: ClientFactory) -> None:
    attempts = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(
            [429, 500, 503][attempts - 1],
            json={"message": f"attempt {attempts}"},
            headers={"x-typesafe-request-id": f"request-{attempts}", "retry-after-ms": "0"},
        )

    with pytest.raises(TypeSafeAPIError) as caught:
        await system_one(clients(handler, retries=True), state="x", questions={"q": Noul(instructions="?")})
    assert attempts == 3
    assert caught.value.status == 503
    assert caught.value.body == {"message": "attempt 3"}
    assert caught.value.request_id == "request-3"
    assert str(caught.value) == "POST https://api.typesafe.ai/v1/systemone: 503 attempt 3 (request_id=request-3)"


async def test_cancel_pending_retry() -> None:
    sleeping = asyncio.Event()

    async def sleep(delay: float) -> None:
        sleeping.set()
        await asyncio.Event().wait()

    async with AsyncTypeSafeClient(
        api_key="test",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: httpx2.Response(429))),
    ) as client:
        client.models._retry = client.models._retry.copy(sleep=sleep)
        task = asyncio.create_task(client.models.list())
        await asyncio.wait_for(sleeping.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.parametrize("max_retries,attempts", [(0, 1), (1, 2), (4, 5)])
async def test_retry_policy_max_retries(clients: ClientFactory, max_retries: int, attempts: int) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(429, json={"message": "slow"}, headers={"retry-after-ms": "0"})

    with pytest.raises(TypeSafeRateLimitError):
        await models(clients(handler, retry=RetryPolicy(max_retries=max_retries)))
    assert len(requests) == attempts


@pytest.mark.parametrize("status,attempts", [(409, 3), (500, 1)])
async def test_retry_policy_custom_statuses(clients: ClientFactory, status: int, attempts: int) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(status, json={"message": "x"}, headers={"retry-after-ms": "0"})

    with pytest.raises(TypeSafeAPIError):
        await models(clients(handler, retry=RetryPolicy(http_statuses={409})))
    assert len(requests) == attempts


async def test_retry_policy_per_call_override(clients: ClientFactory) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(429, json={}, headers={"retry-after-ms": "0"})

    client = clients(handler, retry=RetryPolicy(max_retries=2))
    with pytest.raises(TypeSafeRateLimitError):
        await models(client, retry=RetryPolicy(max_retries=0))
    assert len(requests) == 1


@pytest.mark.parametrize(
    "policy",
    [
        RetryPolicy(max_retries=1, predicate=lambda error: isinstance(error, TypeSafeAPIError) and error.status == 404),
        RetryPolicy(max_retries=1, exceptions={TypeSafeAPIError}),
    ],
)
async def test_retry_policy_exceptions_and_predicate(clients: ClientFactory, policy: RetryPolicy) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(404, json={"message": "gone"}, headers={"retry-after-ms": "0"})

    with pytest.raises(TypeSafeAPIError):
        await models(clients(handler, retry=policy))
    assert len(requests) == 2  # A 404 is not retried by default; the predicate and extra exceptions opt in.


def test_retry_policy_wait_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("random.random", lambda: 0.0)
    error = TypeSafeRateLimitError(429, {}, httpx2.Headers({"Retry-After": "5"}))
    state = RetryCallState(RetryPolicy()._build_tenacity(), None, (), {})
    state.set_exception((type(error), error, None))
    state.attempt_number = 1
    assert RetryPolicy()._wait(state) == 5.0
    assert RetryPolicy(respect_retry_after=False)._wait(state) == 0.5
    assert RetryPolicy(backoff_initial=0.2, respect_retry_after=False)._wait(state) == 0.2


@pytest.mark.parametrize(
    "initial,maximum,attempt,expected",
    [(1e-300, 1e300, 1, 0.0), (1e-300, 1e300, 2000, 1e300), (1e308, 1e308, 1, 1e308), (0.5, 0.0006, 1, 0.0006)],
)
def test_backoff_extreme_values(monkeypatch: pytest.MonkeyPatch, initial: float, maximum: float, attempt: int, expected: float) -> None:
    monkeypatch.setattr("random.random", lambda: 0.0)
    policy = RetryPolicy(backoff_initial=initial, backoff_max=maximum)
    state = RetryCallState(policy._build_tenacity(), None, (), {})
    state.attempt_number = attempt
    assert policy._wait(state) == expected
