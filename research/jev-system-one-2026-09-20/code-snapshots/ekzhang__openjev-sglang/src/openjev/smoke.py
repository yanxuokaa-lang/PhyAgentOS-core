import asyncio
import math
import os
import time

import httpx


async def smoke_test(url: str, timeout: float = 1200) -> dict:
    """Exercise real inference; no mock fallback or fabricated probabilities."""
    headers = {"Modal-Session-ID": "openjev-smoke"}
    if key := os.environ.get("OPENJEV_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    deadline = time.monotonic() + timeout
    waiting_started = time.monotonic()
    async with httpx.AsyncClient(base_url=url.rstrip("/"), headers=headers, timeout=120) as client:
        while True:
            try:
                response = await client.get("/health", timeout=10)
                if response.is_success:
                    break
                if response.status_code not in {502, 503, 504}:
                    response.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("Server did not become healthy")
            await asyncio.sleep(2)
        ready_wait_seconds = time.monotonic() - waiting_started
        startup_seconds = response.json().get("startup_seconds")
        state = [
            {"role": "system", "content": "You are a support assistant."},
            {"role": "user", "content": "My credit card was charged twice. Please refund it."},
        ]
        payload = {
            "model": "jev-latest",
            "state": state,
            "questions": {
                "refund": {"type": "noul", "instructions": "Does the user request a refund?"},
                "team": {
                    "type": "choice",
                    "instructions": "Which department should help?",
                    "criteria": {"billing": "Payments and refunds", "technical": "Software bugs"},
                },
                "urgency": {
                    "type": "score",
                    "instructions": "How urgent is the request?",
                    "criteria": ["Routine", "Urgent", "Emergency"],
                },
                "many": {
                    "type": "choice",
                    "instructions": "Select the description saying this is the target.",
                    "criteria": {
                        **{f"other-{i}": "Not the target" for i in range(63)},
                        "target": "This is the target",
                    },
                },
            },
        }
        started = time.perf_counter()
        result = await client.post("/v1/systemone", json=payload)
        result.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000
        data = result.json()
        assert set(data["answers"]) == set(payload["questions"])
        assert data["usage"]["output_tokens"] == 5, "One warm-up plus four one-token branches"
        for value in data["answers"].values():
            if "probabilities" in value:
                assert math.isclose(sum(value["probabilities"].values()), 1, abs_tol=1e-6)
                assert all(
                    math.isfinite(p) and 0 <= p <= 1 for p in value["probabilities"].values()
                )
                assert 0 <= value["confidence"] <= 1
        assert data["answers"]["refund"]["noul"] > 0.5, "Refund sanity check failed"
        assert data["answers"]["team"]["choice"] == "billing", "Routing sanity check failed"
        assert len(data["answers"]["many"]["probabilities"]) == 64
        assert 0 <= data["answers"]["urgency"]["score"] <= 2
        bad = await client.post(
            "/v1/systemone",
            json={
                "model": "jev-latest",
                "state": "test",
                "questions": {
                    "too_many": {
                        "type": "choice",
                        "instructions": "pick",
                        "criteria": {str(i): f"Option {i}" for i in range(65)},
                    }
                },
            },
        )
        assert bad.status_code == 422, "65 options must be rejected"
        return {
            "url": url,
            "ready_wait_seconds": round(ready_wait_seconds, 2),
            "container_startup_seconds": startup_seconds,
            "latency_ms": round(latency_ms, 2),
            "server_timing": result.headers.get("server-timing"),
            "cached_tokens": (
                int(result.headers["x-openjev-cached-tokens"])
                if "x-openjev-cached-tokens" in result.headers
                else None
            ),
            "prefix_tokens": int(result.headers.get("x-openjev-prefix-tokens", 0)),
            "result": data,
        }
