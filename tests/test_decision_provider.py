from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from PhyAgentOS.agent.decision_provider import (
    DecisionCandidate,
    DecisionRequest,
    DecisionResult,
    JEVHTTPDecisionProvider,
)
from PhyAgentOS.config.schema import DecisionPointConfig


def _request() -> DecisionRequest:
    return DecisionRequest(
        decision_point="query_input_selection",
        task_id="task-1",
        revision_id="revision-1",
        scene_revision="scene-1",
        node_id="bind-1",
        goal="Bind the red object",
        facts={"capability": "scene.bind"},
        candidates=(
            DecisionCandidate(candidate_id="one", description="red object"),
            DecisionCandidate(candidate_id="two", description="blue object"),
        ),
        acceptance_policy_ref="artifact://jev-policy/query-v1",
    )


def test_decision_result_is_closed_to_state_mutation_fields():
    assert DecisionResult(outcome="escalate", reason="ambiguous").selected_id is None
    assert DecisionResult(
        outcome="selected",
        selected_id="one",
        model_version=" jev-1.13.0 ",
    ).model_version == "jev-1.13.0"
    with pytest.raises(ValidationError):
        DecisionResult.model_validate({
            "outcome": "selected",
            "selected_id": "one",
            "task_status": "completed",
        })
    with pytest.raises(ValidationError):
        DecisionResult(outcome="unavailable", selected_id="one")
    with pytest.raises(ValidationError, match="model_version"):
        DecisionResult(outcome="escalate", model_version=" ")


def test_active_decision_config_requires_measured_policy_reference():
    with pytest.raises(ValidationError, match="acceptancePolicyRef"):
        DecisionPointConfig(mode="active", endpoint="http://jev.invalid/choice")
    config = DecisionPointConfig(
        mode="active",
        endpoint="http://jev.invalid/choice",
        model="jev-fixture",
        acceptance_policy_ref="artifact://jev-eval/query-v1",
        timeout_cap_s=1,
        fallback_reserve_s=10,
    )
    assert config.mode == "active"
    with pytest.raises(ValidationError, match="require a model"):
        DecisionPointConfig(
            mode="shadow",
            endpoint="http://jev.invalid/choice",
        )


def test_http_decision_provider_accepts_typed_choice_and_closes():
    async def exercise():
        received = []

        async def handler(request: httpx.Request) -> httpx.Response:
            received.append(request)
            return httpx.Response(200, json={
                "outcome": "selected",
                "selected_id": "one",
                "model_version": "jev-1.13.0",
                "reason": "matches the task goal",
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = JEVHTTPDecisionProvider(client=client)
        result = await provider.decide(
            _request(),
            endpoint="https://jev.invalid/choice",
            model="jev-fixture",
            timeout_s=0.5,
        )
        assert result.outcome == "selected"
        assert result.selected_id == "one"
        assert result.model_version == "jev-1.13.0"
        payload = json.loads(received[0].content)
        assert payload["model"] == "jev-fixture"
        assert payload["request"]["task_id"] == "task-1"
        assert "arguments" not in payload["request"]["candidates"][0]
        await provider.close()
        await provider.close()
        with pytest.raises(RuntimeError, match="closed"):
            await provider.decide(
                _request(), endpoint="https://jev.invalid/choice",
                model="jev-fixture", timeout_s=0.5,
            )
        await client.aclose()

    asyncio.run(exercise())


def test_http_decision_provider_propagates_cancellation():
    async def exercise():
        entered = asyncio.Event()

        async def handler(_request: httpx.Request) -> httpx.Response:
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = JEVHTTPDecisionProvider(client=client)
        task = asyncio.create_task(provider.decide(
            _request(), endpoint="https://jev.invalid/choice",
            model="jev-fixture", timeout_s=10,
        ))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await provider.close()
        await client.aclose()

    asyncio.run(exercise())
