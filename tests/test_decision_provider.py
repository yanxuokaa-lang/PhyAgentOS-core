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


@pytest.mark.parametrize("choice", ["one", "escalate", "unknown"])
@pytest.mark.parametrize("metadata", [{}, {"confidence": 0.57, "probabilities": {"one": 0.68, "escalate": 0.32}}])
def test_systemone_wire_shape_and_model_identity(choice, metadata):
    async def exercise():
        async def handler(request):
            assert request.headers["Authorization"] == "Bearer fixture-key"
            payload = json.loads(request.content)
            assert set(payload) == {"model", "state", "questions"}
            state = json.loads(payload["state"])
            assert state == {
                "decision_point": "query_input_selection",
                "goal": "Bind the red object", "facts": {"capability": "scene.bind"},
            }
            assert payload["questions"]["decision"]["criteria"]["one"] == "red object"
            assert "escalate" in payload["questions"]["decision"]["criteria"]
            return httpx.Response(200, json={
                "model": "jev-1.13.0", "usage": {"input_tokens": 10},
                "answers": {"decision": {"type": "choice", "choice": choice, **metadata}},
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = JEVHTTPDecisionProvider(
                client=client, api_format="systemone", api_key="fixture-key",
            )
            result = await provider.decide(
                _request(), endpoint="https://jev.invalid/systemone",
                model="jev-latest", timeout_s=1,
            )
            assert result.outcome == ("escalate" if choice == "escalate" else "selected")
            assert result.selected_id == (None if choice == "escalate" else choice)
            assert result.model_version == "jev-1.13.0"
            await provider.close()
            assert not client.is_closed  # injected client remains caller-owned

    asyncio.run(exercise())


@pytest.mark.parametrize("body", [
    [], {}, {"answers": []}, {"answers": None},
    {"answers": {"decision": {"type": "choice", "choice": []}}},
    {"answers": {"decision": {"type": "choice", "choice": "one", "arguments": {}}}},
    {"answers": {"decision": {"type": "text", "choice": "one"}}},
])
def test_systemone_malformed_answer_is_rejected(body):
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=body)
        )) as client:
            provider = JEVHTTPDecisionProvider(client=client, api_format="systemone")
            with pytest.raises(ValueError, match="invalid systemone"):
                await provider.decide(
                    _request(), endpoint="https://jev.invalid/systemone",
                    model="jev-latest", timeout_s=1,
                )
    asyncio.run(exercise())


def test_factory_routes_protocol_and_credentials_by_enabled_point(tmp_path, monkeypatch):
    from PhyAgentOS.cli.commands import _make_decision_provider
    from PhyAgentOS.config.schema import Config

    key_path = tmp_path / "key"
    key_path.write_text("file-fixture-key\n")
    key_path.chmod(0o600)
    monkeypatch.setenv("RECOVERY_FIXTURE_KEY", "recovery-fixture-key")
    config = Config()
    config._config_path = tmp_path / "config.json"
    config.agents.decisions.query_input_selection = DecisionPointConfig(
        mode="shadow", endpoint="https://query.invalid", model="jev",
        api_key_file="key", api_format="systemone",
    )
    config.agents.decisions.method_fragment_selection = DecisionPointConfig(
        api_key_env="MUST_NOT_BE_READ",
    )
    config.agents.decisions.recovery_method_selection = DecisionPointConfig(
        mode="shadow", endpoint="https://recovery.invalid", model="typed",
        api_key_env="RECOVERY_FIXTURE_KEY",
    )

    async def exercise():
        provider = _make_decision_provider(config)
        clients = []
        for name, child in provider._providers.items():
            await child._client.aclose()

            def handler(request, point=name):
                payload = json.loads(request.content)
                if point == "query_input_selection":
                    assert request.headers["Authorization"] == "Bearer file-fixture-key"
                    assert "state" in payload
                    return httpx.Response(200, json={
                        "model": "jev-version", "answers": {
                            "decision": {"type": "choice", "choice": "one"},
                        },
                    })
                assert request.headers["Authorization"] == "Bearer recovery-fixture-key"
                assert "request" in payload
                return httpx.Response(200, json={"outcome": "escalate"})

            child._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            clients.append(child._client)
            result = await provider.decide(
                _request().model_copy(update={"decision_point": name}),
                endpoint=getattr(config.agents.decisions, name).endpoint,
                model="test", timeout_s=1,
            )
            assert result.outcome == ("selected" if name == "query_input_selection" else "escalate")
        disabled = await provider.decide(
            _request().model_copy(update={"decision_point": "method_fragment_selection"}),
            endpoint="https://disabled.invalid", model="test", timeout_s=1,
        )
        assert disabled.outcome == "unavailable"
        await provider.close()
        await provider.close()
        assert all(client.is_closed for client in clients)

    asyncio.run(exercise())


def test_decision_credentials_fail_before_client_creation(monkeypatch):
    from PhyAgentOS.cli.commands import _make_decision_provider
    from PhyAgentOS.config.schema import Config

    with pytest.raises(ValidationError, match="choose only one"):
        DecisionPointConfig(api_key_env="KEY", api_key_file="key")
    config = Config()
    config.agents.decisions.query_input_selection.api_key_file = "/missing/unused"
    assert _make_decision_provider(config) is None
    config.agents.decisions.query_input_selection = DecisionPointConfig(
        mode="shadow", endpoint="https://jev.invalid", model="jev", api_key_env="ABSENT_JEV_TEST_KEY",
    )
    monkeypatch.delenv("ABSENT_JEV_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="missing API key environment"):
        _make_decision_provider(config)


@pytest.mark.parametrize("api_format", ["typed", "systemone"])
def test_http_decision_provider_propagates_cancellation(api_format):
    async def exercise():
        entered = asyncio.Event()

        async def handler(_request: httpx.Request) -> httpx.Response:
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = JEVHTTPDecisionProvider(client=client, api_format=api_format)
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
