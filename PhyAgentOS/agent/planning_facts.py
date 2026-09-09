"""Read persisted Gateway response envelopes without conflating input and effects."""

from typing import Any


def response_facts(response: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    payload = response.get("data")
    payload = payload if isinstance(payload, dict) else response
    result = payload.get("result")
    if isinstance(result, dict):
        payload = {**payload, **result}
    summary = payload.get("capability_outcome_summary")
    if isinstance(summary, dict):
        payload = {**payload, **summary}
    return payload
