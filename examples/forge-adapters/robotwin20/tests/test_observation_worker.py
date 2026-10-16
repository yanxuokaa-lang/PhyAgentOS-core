import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

from robotwin_observation_worker import _observation_payload


class Provider:
    def __init__(self):
        self.calls = []

    def observe(self, sensor_ref):
        self.calls.append(("observe", sensor_ref))
        return Snapshot(
            captured_at=datetime(2026, 10, 16, tzinfo=timezone.utc), scene_revision="scene-1",
            frame_id="head_camera", calibration_ref="artifact://scene-1/calibration",
            artifacts=({"ref": "artifact://scene-1/rgb", "kind": "rgb", "media_type": "image/png"},),
            sensor_available=True, observation_ref="observation://scene-1/head_camera",
        )

    def observe_many(self, sensor_refs):
        self.calls.append(("observe_many", tuple(sensor_refs)))
        return tuple(self.observe(sensor_ref) for sensor_ref in sensor_refs)


@dataclass
class Snapshot:
    captured_at: datetime
    scene_revision: str
    frame_id: str
    calibration_ref: str
    artifacts: tuple[dict[str, str], ...]
    sensor_available: bool
    observation_ref: str


def test_observation_worker_projects_synchronized_views_without_actions():
    provider = Provider()
    result = _observation_payload(provider, {"sensor_refs": ["camera/head", "camera/front"]})
    assert result["sensor_ref"] == "camera/head"
    assert [view["sensor_ref"] for view in result["views"]] == ["camera/head", "camera/front"]
    assert provider.calls[0] == ("observe_many", ("camera/head", "camera/front"))


def test_observation_worker_rejects_missing_sensor():
    provider = Provider()
    with pytest.raises(ValueError, match="sensor_ref"):
        _observation_payload(provider, {})
    assert provider.calls == []
