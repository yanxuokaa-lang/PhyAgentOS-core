"""Typed, side-effect-free choice decisions for Agent-owned control points."""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DecisionCandidate(BaseModel):
    """One host-materialized choice; provider output may only name its ID."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    description: str

    @field_validator("candidate_id", "description")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("decision candidate fields must be non-empty")
        return value


class DecisionRequest(BaseModel):
    """Minimal host facts for one bounded choice request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_point: str
    task_id: str
    revision_id: str
    scene_revision: str
    node_id: str | None = None
    goal: str
    facts: dict[str, Any] = Field(default_factory=dict)
    candidates: tuple[DecisionCandidate, ...] = Field(min_length=2)
    acceptance_policy_ref: str | None = None

    @field_validator(
        "decision_point", "task_id", "revision_id", "scene_revision", "goal"
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("decision identity and goal fields must be non-empty")
        return value

    @model_validator(mode="after")
    def unique_candidates(self) -> "DecisionRequest":
        candidate_ids = [item.candidate_id for item in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("decision candidate IDs must be unique")
        return self


class DecisionResult(BaseModel):
    """Closed provider result; no task mutation or execution fields are accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: Literal["selected", "escalate", "unavailable"]
    selected_id: str | None = None
    model_version: str | None = None
    reason: str = ""

    @field_validator("model_version")
    @classmethod
    def nonempty_model_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("model_version must be non-empty when provided")
        return value

    @model_validator(mode="after")
    def selected_shape(self) -> "DecisionResult":
        if self.outcome == "selected":
            if not isinstance(self.selected_id, str) or not self.selected_id.strip():
                raise ValueError("selected decision requires selected_id")
        elif self.selected_id is not None:
            raise ValueError("only selected decisions may include selected_id")
        return self


@runtime_checkable
class DecisionProvider(Protocol):
    """External read-only choice service; the host remains the sole state owner."""

    async def decide(
        self,
        request: DecisionRequest,
        *,
        endpoint: str,
        model: str,
        timeout_s: float,
    ) -> DecisionResult:
        """Return one closed choice outcome without mutating host state."""

    async def close(self) -> None:
        """Release provider resources."""


class JEVHTTPDecisionProvider:
    """HTTP adapter for the typed JEV choice endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = client or httpx.AsyncClient(headers=headers)
        self._owns_client = client is None
        self._closed = False

    async def decide(
        self,
        request: DecisionRequest,
        *,
        endpoint: str,
        model: str,
        timeout_s: float,
    ) -> DecisionResult:
        if self._closed:
            raise RuntimeError("decision provider is closed")
        response = await self._client.post(
            endpoint,
            json={
                "model": model,
                "request": request.model_dump(mode="json"),
            },
            timeout=timeout_s,
        )
        response.raise_for_status()
        return DecisionResult.model_validate(response.json())

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_client:
            await self._client.aclose()


__all__ = [
    "DecisionCandidate",
    "DecisionProvider",
    "DecisionRequest",
    "DecisionResult",
    "JEVHTTPDecisionProvider",
]
