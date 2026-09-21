from types import SimpleNamespace

import pytest

from robotwin20_adapter.oracle_grasp import (
    OracleGraspProviderError,
    PersistentOracleGraspProvider,
)


def _response():
    return {
        "ok": True,
        "request_id": "worker-request-1",
        "holding_state": "empty",
        "owner": None,
        "acquire_invocation_id": None,
        "entity_ref": None,
        "candidates": [{"provenance": ["artifact://observation/geometry"]}],
        "ambiguities": [],
        "funnel": {"decoded": 0, "canonicalized": 0, "deduplicated": 0, "retained": 0},
        "provider_available": True,
        "motion_authorized": False,
        "geometry_source": "oracle_actor",
        "oracle_evidence_ref": "artifact://persistent/epoch/oracle-grasp",
    }


def test_oracle_provider_uses_private_read_only_worker_query():
    calls = []
    grounding_calls = []
    client = SimpleNamespace(
        query=lambda operation, arguments: calls.append((operation, arguments)) or _response()
    )
    transform = list(range(16))
    provider = PersistentOracleGraspProvider(
        client,
        provider_to_contact_flat=transform,
        grounding=SimpleNamespace(
            activate_observed_entities=lambda request: grounding_calls.append(request)
            or "artifact://bindings/current"
        ),
    )

    result = provider.propose({"scene_revision": "scene-4", "targets": []})

    assert result == {
        "candidates": [{
            "provenance": [
                "artifact://observation/geometry",
                "artifact://persistent/epoch/oracle-grasp",
            ]
        }],
        "ambiguities": [],
        "funnel": {"decoded": 0, "canonicalized": 0, "deduplicated": 0, "retained": 0},
        "provider_available": True,
        "produced_evidence_refs": ["artifact://persistent/epoch/oracle-grasp"],
    }
    assert calls == [
        (
            "oracle_grasp_candidates",
            {
                "request": {"scene_revision": "scene-4", "targets": []},
                "provider_T_contact_center": transform,
                "binding_ref": "artifact://bindings/current",
            },
        )
    ]
    assert grounding_calls == [{"scene_revision": "scene-4", "targets": []}]


@pytest.mark.parametrize(
    "change",
    [
        {"motion_authorized": True},
        {"geometry_source": "observation"},
        {"oracle_evidence_ref": "not-an-artifact"},
    ],
)
def test_oracle_provider_rejects_invalid_worker_provenance(change):
    response = {**_response(), **change}
    provider = PersistentOracleGraspProvider(
        SimpleNamespace(query=lambda *_args, **_kwargs: response),
        provider_to_contact_flat=list(range(16)),
        grounding=SimpleNamespace(
            activate_observed_entities=lambda _request: "artifact://bindings/current"
        ),
    )

    with pytest.raises(OracleGraspProviderError, match="provenance"):
        provider.propose({})
