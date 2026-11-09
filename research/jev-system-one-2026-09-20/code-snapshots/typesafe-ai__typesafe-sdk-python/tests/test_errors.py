import copy
import pickle
import traceback
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

import httpx2
import pytest

from tests.conftest import ClientFactory
from tests.helpers import models, system_one
from typesafe_sdk import (
    ListModelsResponse,
    Noul,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeBadRequestError,
    TypeSafeError,
    TypeSafeInternalServerError,
    TypeSafeNotFoundError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
    TypeSafeUnprocessableEntityError,
)


@pytest.mark.parametrize(
    "error",
    [
        TypeSafeError("SDK failure"),
        TypeSafeAPIConnectionError("Connection failure"),
        TypeSafeAPIError(status=500, body=None, headers=httpx2.Headers()),
        TypeSafeAPIError(400, {}, httpx2.Headers(), message=""),
        TypeSafeBadRequestError(400, {"message": "Bad request"}, httpx2.Headers()),
        TypeSafeAuthenticationError(401, {}, httpx2.Headers()),
        TypeSafePermissionDeniedError(403, {}, httpx2.Headers()),
        TypeSafeNotFoundError(404, {}, httpx2.Headers()),
        TypeSafeUnprocessableEntityError(422, {}, httpx2.Headers()),
        TypeSafeInternalServerError(503, {}, httpx2.Headers()),
        TypeSafeRateLimitError(429, {}, httpx2.Headers({"retry-after-ms": "125", "x-typesafe-request-id": "req-rate"})),
        TypeSafeAPIResponseValidationError(200, {}, httpx2.Headers(), field_path="answers.q.noul"),
        TypeSafeAPITimeoutError(timeout=1.0),
        TypeSafeAPITimeoutError(timeout=httpx2.Timeout(1.0, read=2.0)),
    ],
    ids=lambda error: type(error).__name__,
)
def test_exception_reconstruction(error: TypeSafeError) -> None:
    assert repr(error) == f"{type(error).__name__}({str(error)!r})"
    unpickled = pickle.loads(pickle.dumps(error))  # noqa: S301 - Round-tripping an exception created in this test.
    for restored in (type(error)(*error.args), copy.copy(error), copy.deepcopy(error), unpickled):
        assert restored is not error
        assert type(restored) is type(error)
        assert str(restored) == str(error)
        assert repr(restored) == repr(error)
        assert restored.args == error.args
        assert vars(restored) == vars(error)


def _raise_api_error() -> None:
    raise TypeSafeBadRequestError(
        400,
        {"message": "Bad request"},
        httpx2.Headers({"x-typesafe-request-id": "req-worker"}),
        endpoint="POST https://example.test/v1/systemone",
    )


def test_api_error_from_process_pool() -> None:
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        future = pool.submit(_raise_api_error)
        with pytest.raises(TypeSafeBadRequestError, match="400 Bad request") as caught:
            future.result(timeout=10)
        assert caught.value.status == 400
        assert caught.value.body == {"message": "Bad request"}
        assert caught.value.request_id == "req-worker"
        assert caught.value.endpoint == "POST https://example.test/v1/systemone"
        assert pool.submit(abs, -1).result(timeout=10) == 1


@pytest.mark.parametrize("resource", ["models", "system_one"])
async def test_api_error_request_context(clients: ClientFactory, resource: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, json={"message": "Too many requests"}, headers={"x-typesafe-request-id": "req-context"})

    client = clients(handler, api_key="private-api-key", base_url="https://api.example.test/prefix")
    call = models(client) if resource == "models" else system_one(client, state="hello", questions={"q": Noul(instructions="Greeting?")})
    with pytest.raises(TypeSafeRateLimitError) as caught:
        await call
    endpoint = "GET https://api.example.test/prefix/v1/models" if resource == "models" else "POST https://api.example.test/prefix/v1/systemone"
    error = caught.value
    expected = f"{endpoint}: 429 Too many requests (request_id=req-context)"
    assert error.endpoint == endpoint
    assert str(error) == expected
    assert expected in "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert "private-api-key" not in repr(error)
    unpickled = pickle.loads(pickle.dumps(error))  # noqa: S301 - Round-tripping a locally created exception.
    assert unpickled.endpoint == endpoint
    assert str(unpickled) == expected


def test_api_error_endpoint_omits_url_credentials() -> None:
    request = httpx2.Request("GET", "https://user:password@example.test/v1/models?token=secret#fragment")
    response = httpx2.Response(400, json={"message": "Bad request"}, request=request)
    with pytest.raises(TypeSafeBadRequestError) as caught:
        ListModelsResponse.from_http_response(response)
    assert str(caught.value) == "GET https://example.test/v1/models: 400 Bad request"
    assert caught.value.endpoint == "GET https://example.test/v1/models"


@pytest.mark.parametrize(
    "error_type",
    [
        TypeSafeAPIError,
        TypeSafeBadRequestError,
        TypeSafeAuthenticationError,
        TypeSafePermissionDeniedError,
        TypeSafeNotFoundError,
        TypeSafeUnprocessableEntityError,
        TypeSafeRateLimitError,
        TypeSafeInternalServerError,
    ],
)
@pytest.mark.parametrize("message", ["A custom explanation", ""])
def test_message_override(error_type: type[TypeSafeAPIError], message: str) -> None:
    headers = httpx2.Headers({"retry-after-ms": "125"})
    body = {"message": "Server explanation"}
    error = error_type(429, body, headers, message=message)
    assert str(error) == (f"429 {message}" if message else "429")
    assert error.status == 429
    assert error.body is body
    assert error.headers is headers
    assert error.request_id is None
    if isinstance(error, TypeSafeRateLimitError):
        assert error.retry_after_ms == 125


@pytest.mark.parametrize(
    "body,message",
    [
        (b"", "400 status code (no body)"),
        (b"null", "400 status code (no body)"),
        (b"[]", "400 []"),
        (b"42", "400 42"),
        (b"not JSON: \xff", "400 not JSON: \ufffd"),
        pytest.param(b"x" * 201, "400 " + "x" * 201, id="long-plain-message"),
        pytest.param(b'{"unknown":"' + b"x" * 201 + b'"}', '400 {"unknown":"' + "x" * 188 + "…", id="long-unstructured-body"),
        (b'{"error":"","message":"ignored"}', '400 {"error":"","message":"ignored"}'),
        (b'{"detail":[null,42,{"msg":4}]}', '400 {"detail":[null,42,{"msg":4}]}'),
    ],
)
async def test_error_body_edge_cases(clients: ClientFactory, body: bytes, message: str) -> None:
    with pytest.raises(TypeSafeAPIError) as caught:
        await models(clients(lambda request: httpx2.Response(400, content=body)))
    assert str(caught.value) == f"GET https://api.typesafe.ai/v1/models: {message}"
    assert caught.value.request_id is None
