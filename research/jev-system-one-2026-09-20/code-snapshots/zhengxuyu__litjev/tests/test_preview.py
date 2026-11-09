from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient

from litjev.games.preview import create_preview_app


def test_random_preview_runs_real_doom_without_model():
    with TestClient(create_preview_app(seed=7, max_steps=2, resolution="160x120")) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert 'id="probabilities"' in page.text
        assert 'id="trace-data"' in page.text
        assert 'id="live-config" type="application/json">true' in page.text
        assert "先让随机策略玩起来" not in page.text
        initial = client.get("/state").json()
        assert initial["policy"] == "uniform_random"
        assert initial["step"] == 0
        assert initial["frame"].startswith("data:image/png;base64,")
        first = client.post("/step").json()
        assert first["action"] in first["actions"]
        assert first["step"] == 1
        assert first["forward_calls"] == 0
        assert sum(first["probabilities"]) == pytest.approx(1)
        assert client.post("/step").json()["done"]
        assert client.post("/step").json()["episode"] == 2
        reset = client.post("/reset").json()
        assert reset["step"] == 0 and reset["episode"] == 3


def test_background_loop_controls_and_latest_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = create_preview_app(seed=7, resolution="160x120", recording="recordings")
    with TestClient(app) as client:
        assert not client.get("/state").json()["running"]
        assert client.post("/control", json={"running": True, "fps": 18}).status_code == 200
        deadline = monotonic() + 3
        while client.get("/state").json()["step"] < 2 and monotonic() < deadline:
            sleep(0.02)
        assert client.get("/state").json()["step"] >= 2
        assert client.post("/step").status_code == 409
        stopped = client.post("/control", json={"running": False}).json()
        sleep(0.15)
        assert client.get("/state").json()["step"] == stopped["step"]
        assert stopped["history"][-1]["step"] == stopped["step"]
        assert len(stopped["history"]) <= 90
        assert client.post("/control", json={"fps": 10000}).status_code == 422
    recordings = list(tmp_path.rglob("*.lmp"))
    assert recordings and recordings[0].stat().st_size > 0
