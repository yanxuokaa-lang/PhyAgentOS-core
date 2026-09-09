from pathlib import Path

import pytest
import yaml
from test_arm_candidates import _profile

from robotwin20_adapter.persistent_deployment import build_persistent_deployment


def test_deployment_wires_shared_cache_and_requires_persistent_stop_policy(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"
    arguments = {"arm-planning-profile": str(arm),
                 "route-input-profile": str(profiles / "route-inputs-persistent.yaml")}
    client = object()
    deployment = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
        arm_profile_digest="a" * 64,
    )
    assert deployment.preparation_provider.client is client
    assert deployment.preparation_provider.prepared_routes is deployment.prepared_routes
    assert deployment.runtime_arguments()["resolve_preparation"] is deployment.prepared_routes
    assert deployment.capability_provider.client is client
    arguments["route-input-profile"] = str(profiles / "route-inputs.yaml")
    with pytest.raises(ValueError, match="hold_and_reconcile"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64,
        )
