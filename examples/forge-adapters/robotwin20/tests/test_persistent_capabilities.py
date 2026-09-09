import json

import yaml
from PhyAgentOS.forge.capability_runtime.manipulation_capabilities import CapabilitySnapshotEndpoint
from test_arm_candidates import _profile

from robotwin20_adapter.persistent_capabilities import PersistentCapabilityProvider
from robotwin20_adapter.route_evidence import _artifact_path


def test_public_capability_snapshot_persists_and_rejects_previous_scene(tmp_path):
    profile = tmp_path / "arms.yaml"
    profile.write_text(yaml.safe_dump(_profile()))
    (tmp_path / "capture").mkdir()
    (tmp_path / "capture/calibration.json").write_text("{}")

    class Client:
        revision = "scene-1"

        def query(self, operation, arguments):
            return {"scene_revision": self.revision}

    client = Client()
    provider = PersistentCapabilityProvider(client=client, artifact_root=tmp_path,
                                            arm_profile=profile, profile_digest="a" * 64)
    endpoint = CapabilitySnapshotEndpoint(provider)
    request = {"scene_revision": "scene-1", "observation_ref": "observation://scene-1/camera",
               "calibration_ref": "artifact://capture/calibration"}
    first = endpoint.invoke(request)
    assert first["status"] == "available"
    assert first["motion_authorized"] is False
    assert endpoint.invoke(request) == first
    persisted = json.loads(_artifact_path(tmp_path, first["snapshot_ref"]).read_text())
    assert persisted == {key: value for key, value in first.items() if key != "status"}
    client.revision = "scene-2"
    assert endpoint.invoke(request)["status"] == "unavailable"
    request.update(scene_revision="scene-2", observation_ref="observation://scene-2/camera")
    second = endpoint.invoke(request)
    assert second["status"] == "available"
    assert second["snapshot_ref"] != first["snapshot_ref"]
