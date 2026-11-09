import pytest
from fastapi.testclient import TestClient
from von.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_list_models(client):
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    ids = [m["id"] for m in data["data"]]
    assert "von-latest" in ids
    assert "von-1.0.0" in ids


def test_system_one_post(client):
    payload = {
        "model": "von-latest",
        "state": "The user clicked the checkout button but received a credit card decline error.",
        "questions": {
            "error_type": {
                "type": "choice",
                "instructions": "What type of error occurred?",
                "criteria": {
                    "payment_error": "Payment or card transaction failure",
                    "ui_bug": "Layout or display bug",
                },
            },
            "is_payment": {
                "type": "noul",
                "instructions": "Is this a payment failure?",
            },
        },
    }
    res = client.post("/v1/systemone", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "von-1.0.0"
    assert "error_type" in data["answers"]
    assert data["answers"]["error_type"]["choice"] == "payment_error"
    assert data["answers"]["is_payment"]["noul"] > 0.5
