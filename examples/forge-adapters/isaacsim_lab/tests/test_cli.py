import json
from types import SimpleNamespace

import pytest

from isaacsim_lab import cli


@pytest.mark.parametrize("status,exit_code", [("available", 0), ("unavailable", 2)])
def test_observation_cli_captures_and_closes_without_cycle_execution(monkeypatch, capsys, status, exit_code):
    calls = []
    class Backend:
        def __init__(self, profile, *, observation_artifact_root):
            calls.append(("construct", observation_artifact_root))
        def observe(self, request):
            calls.append(request)
            return {"status": status, "artifacts": []}
        def close(self):
            calls.append("close")
    monkeypatch.setattr(cli, "LabUtopiaBackend", Backend)
    monkeypatch.setattr(cli.LabUtopiaProfile, "from_json", lambda _: SimpleNamespace())
    monkeypatch.setattr("sys.argv", ["paos-isaacsim-lab-input", "--profile", "deployment.json",
                                    "--observe", "--sensor-ref", "sensor://front"])
    assert cli.main() == exit_code
    assert calls == [("construct", None), {"sensor_refs": ["sensor://front"]}, "close"]
    assert json.loads(capsys.readouterr().out)["status"] == status
