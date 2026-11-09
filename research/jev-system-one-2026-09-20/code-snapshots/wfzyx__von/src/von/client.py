"""Client classes for Von (supporting local in-memory execution and remote HTTP)."""

import os
from typing import Any, Dict, Optional, Union
import httpx

from .engine import VonEngine
from .types import Question, SystemOneResponse


class VonClient:
    """Client for executing Von System One queries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        local: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize Von client.

        If `base_url` is provided or `local=False`, queries are sent over HTTP.
        Otherwise, queries are executed locally in-process via `VonEngine` (zero network latency).
        """
        self.api_key = api_key or os.environ.get("VON_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
        self.base_url = base_url or os.environ.get("VON_BASE_URL")
        self.local = local and (self.base_url is None)
        self.timeout = timeout
        if not self.local and not self.base_url:
            self.base_url = "http://localhost:8000"

    def system_one(
        self,
        state: Any,
        questions: Dict[str, Union[Question, Dict[str, Any]]],
        model: str = "von-latest",
    ) -> SystemOneResponse:
        """Evaluate a state and questions using System One."""
        if self.local:
            engine = VonEngine.get_instance()
            return engine.evaluate(state=state, questions=questions, model=model)

        url = f"{self.base_url.rstrip('/')}/v1/systemone"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model,
            "state": state,
            "questions": {
                qid: (q.model_dump() if hasattr(q, "model_dump") else q)
                for qid, q in questions.items()
            },
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return SystemOneResponse(**data)


class AsyncVonClient:
    """Asynchronous client for executing Von queries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        local: bool = True,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("VON_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
        self.base_url = base_url or os.environ.get("VON_BASE_URL")
        self.local = local and (self.base_url is None)
        self.timeout = timeout
        if not self.local and not self.base_url:
            self.base_url = "http://localhost:8000"

    async def system_one(
        self,
        state: Any,
        questions: Dict[str, Union[Question, Dict[str, Any]]],
        model: str = "von-latest",
    ) -> SystemOneResponse:
        """Evaluate a state and questions asynchronously."""
        if self.local:
            engine = VonEngine.get_instance()
            return engine.evaluate(state=state, questions=questions, model=model)

        url = f"{self.base_url.rstrip('/')}/v1/systemone"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model,
            "state": state,
            "questions": {
                qid: (q.model_dump() if hasattr(q, "model_dump") else q)
                for qid, q in questions.items()
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return SystemOneResponse(**data)
