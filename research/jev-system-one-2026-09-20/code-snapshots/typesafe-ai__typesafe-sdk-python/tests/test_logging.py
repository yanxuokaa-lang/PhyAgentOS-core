import logging

import httpx2
import pytest

from tests.conftest import ClientFactory
from tests.helpers import models
from typesafe_sdk import RetryPolicy, TypeSafeAPIError
from typesafe_sdk._core.logging import logger, setup_logging


@pytest.mark.parametrize("status", [200, 400, 429])
@pytest.mark.parametrize(
    "header",
    [
        "Authorization",
        "Proxy-Authorization",
        "X-API-Key",
        "API-Key",
        "Cookie",
        "Set-Cookie",
        "X-Access-Token",
        "X-Client-Secret",
        "x-MiXeD-ToKeN",
    ],
)
async def test_secret_headers_redacted(
    clients: ClientFactory,
    caplog: pytest.LogCaptureFixture,
    status: int,
    header: str,
) -> None:
    attempts = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(
            status,
            json={"models": []} if status == 200 else {"message": "failure"},
            headers={header: "response-credential", "x-visible": "response-visible"},
        )

    policy = RetryPolicy(backoff_initial=0.001, backoff_max=0.001)
    with caplog.at_level(logging.DEBUG, logger="typesafe_sdk"):
        client = clients(
            handler,
            api_key="auth-credential",
            headers={header: "request-credential", "x-visible": "request-visible"},
            retry=policy,
        )
        if status == 200:
            await models(client)
        else:
            with pytest.raises(TypeSafeAPIError):
                await models(client)
    assert attempts == (3 if status == 429 else 1)
    assert "request-visible" in caplog.text
    assert "response-visible" in caplog.text
    assert "***" in caplog.text
    for secret in ("auth-credential", "request-credential", "response-credential"):
        assert secret not in caplog.text
    if status == 429:
        assert "retry 1" in caplog.text
        assert "retry 2" in caplog.text


@pytest.mark.parametrize(
    "level,expected",
    [
        (logging.DEBUG, {logging.DEBUG, logging.INFO}),
        (logging.INFO, {logging.INFO}),
        (logging.WARNING, set()),
    ],
)
async def test_logger_level_controls_output(
    clients: ClientFactory,
    caplog: pytest.LogCaptureFixture,
    level: int,
    expected: set[int],
) -> None:
    with caplog.at_level(level, logger="typesafe_sdk"):
        await models(clients(lambda request: httpx2.Response(200, json={"models": []})))
    records = [record for record in caplog.records if record.name == "typesafe_sdk"]
    assert {record.levelno for record in records} == expected
    if logging.INFO in expected:
        summaries = [record.getMessage() for record in records if record.levelno == logging.INFO]
        assert len(summaries) == 1
        assert "GET" in summaries[0]
    if logging.DEBUG not in expected:
        assert all("headers=" not in record.getMessage() for record in records)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("off", logging.CRITICAL + 1),
        ("bogus", logging.NOTSET),
        ("", logging.NOTSET),
    ],
)
def test_setup_logging_from_env(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    original = logger.level
    try:
        logger.setLevel(logging.NOTSET)
        monkeypatch.setenv("TYPESAFE_LOG_LEVEL", value)
        setup_logging()
        assert logger.level == expected
    finally:
        logger.setLevel(original)
