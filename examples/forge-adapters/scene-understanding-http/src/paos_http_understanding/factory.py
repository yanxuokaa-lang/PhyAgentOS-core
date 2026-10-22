"""Generic HTTP/JSON transport for deployment-owned scene understanding."""

from __future__ import annotations

import base64
import math
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx


def _json_compatible(value: Any) -> Any:
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


class HttpJsonInference:
    """Send a PAOS inference request to a deployment-configured JSON service."""

    def __init__(
        self,
        *,
        endpoint: str,
        timeout_s: float,
        headers: Mapping[str, str],
    ) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.headers = dict(headers)

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = dict(request)
        artifacts = payload.get("resolved_artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("scene-understanding request has no resolved artifact list")
        payload["resolved_artifacts"] = [
            {
                **{key: value for key, value in artifact.items() if key != "data"},
                "data_base64": _json_compatible(artifact["data"]),
            }
            if isinstance(artifact, dict) and isinstance(artifact.get("data"), bytes)
            else _json_compatible(artifact)
            for artifact in artifacts
        ]
        response = httpx.post(
            self.endpoint,
            json=_json_compatible(payload),
            headers=self.headers,
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, Mapping):
            raise TypeError("scene-understanding HTTP response must be a JSON object")
        return result


class HttpJsonInferenceFactory:
    """Construct the provider-neutral HTTP inference from deployment settings."""

    inference_id = "http_json"

    def create(self, *, configuration: Mapping[str, Any]) -> HttpJsonInference:
        endpoint = configuration.get("endpoint")
        if not isinstance(endpoint, str):
            raise ValueError("HTTP inference endpoint must be a URL")
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("HTTP inference endpoint must use http or https")

        configured_timeout = configuration.get("timeout_s", 30.0)
        if not isinstance(configured_timeout, (int, float)) or isinstance(configured_timeout, bool):
            raise ValueError("HTTP inference timeout_s must be a positive finite number")
        try:
            timeout_s = float(configured_timeout)
        except (OverflowError, ValueError) as exc:
            raise ValueError("HTTP inference timeout_s must be a positive finite number") from exc
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("HTTP inference timeout_s must be a positive finite number")

        headers = configuration.get("headers", {})
        if not isinstance(headers, Mapping) or any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in headers.items()
        ):
            raise ValueError("HTTP inference headers must be a string mapping")

        token_env = configuration.get("token_env")
        if token_env is not None:
            if not isinstance(token_env, str) or not token_env:
                raise ValueError("HTTP inference token_env must be a non-empty environment name")
            token = os.environ.get(token_env)
            if not token:
                raise ValueError(f"HTTP inference credential is not configured: {token_env}")
            headers = {**headers, "Authorization": f"Bearer {token}"}

        return HttpJsonInference(
            endpoint=endpoint,
            timeout_s=timeout_s,
            headers=headers,
        )


__all__ = ["HttpJsonInference", "HttpJsonInferenceFactory"]
