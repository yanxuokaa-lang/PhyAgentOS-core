"""Shared HTTP client for OpenAI-compatible chat-completions endpoints.

stdlib only. One request builder used by the naive-JSON baseline (text
content) and the slots backend (raw choice dicts with logprobs).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

__all__ = ["ChatCompletionsError", "chat_completions_raw", "extract_content"]


class ChatCompletionsError(RuntimeError):
    """A chat-completions call failed (non-2xx response, or no choices)."""

    def __init__(self, status: int, body: str):
        self.status = status
        snippet = body[:200]
        super().__init__(f"chat/completions returned {status}: {snippet}")


def chat_completions_raw(
    base_url: str,
    model: str,
    messages: list[dict],
    *,
    api_key: str | None,
    timeout: float = 120.0,
    temperature: float = 0.0,
    extra_payload: dict | None = None,
) -> dict:
    """POST to ``{base_url}/chat/completions`` and return the first choice dict.

    ``extra_payload`` merges into the request body (max_tokens, logprobs,
    response_format, ...). Raises ChatCompletionsError on any non-2xx response with
    the status and the first 200 chars of the body, and when the response
    carries no choices.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if extra_payload:
        payload.update(extra_payload)
    headers = {"Content-Type": "application/json"}
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise ChatCompletionsError(e.code, e.read().decode("utf-8", errors="replace")) from e
    choices = json.loads(body).get("choices") or []
    if not choices:
        raise ChatCompletionsError(200, f"no choices in response body: {body[:200]}")
    return choices[0]


def extract_content(choice: dict) -> str:
    """The assistant content of a choice dict ('' when absent)."""
    return ((choice.get("message") or {}).get("content")) or ""
