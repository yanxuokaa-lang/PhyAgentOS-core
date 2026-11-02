"""Pure configuration/readback tests and optional native USD composition tests."""
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from isaacsim_lab.scene_physics import (
    apply_scene_physics,
    load_physics_config,
    read_runtime_physics,
)


def profile():
    return load_physics_config(Path(__file__).parents[1] / "configs/labutopia-mixture-physics.json")


@pytest.mark.parametrize("key,value", [("mass_kg", 0), ("mass_kg", float("nan")),
                                      ("mass_kg", True), ("hull_vertex_limit", 2)])
def test_invalid_physics_rejected_before_stage_access(tmp_path, key, value):
    config = profile()
    config["bodies"][0][key] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_physics_config(path)


def test_runtime_readback_uses_replacement_view_not_configured_mass():
    report = {"bodies": [{"path": "/alternative/beaker", "configured_mass_kg": .1}]}
    calls = []
    def factory(path):
        calls.append(path)
        return SimpleNamespace(initialize=lambda: calls.append("initialized"), get_masses=lambda: [.1],
                               get_inertias=lambda: [np.eye(3) * .0001],
                               get_coms=lambda: ([[.01, 0, 0]], [[1, 0, 0, 0]]))
    result = read_runtime_physics(report, rigid_factory=factory)
    assert calls == ["/alternative/beaker", "initialized"]
    assert result["bodies"][0]["measured_com_local_m"] == [.01, 0, 0]
    assert "measured_mass_kg" not in report["bodies"][0]


@pytest.mark.parametrize("mass,inertia", [(.00001, np.eye(3)), (.1, np.zeros((3, 3))),
                                          (float("nan"), np.eye(3))])
def test_bad_runtime_mass_or_inertia_cannot_be_reported_as_success(mass, inertia):
    def factory(_):
        return SimpleNamespace(initialize=lambda: None, get_masses=lambda: [mass],
                               get_inertias=lambda: [inertia],
                               get_coms=lambda: ([[0, 0, 0]], [[1, 0, 0, 0]]))
    with pytest.raises(ValueError):
        read_runtime_physics({"bodies": [{"path": "/body", "configured_mass_kg": .1}]}, rigid_factory=factory)


def usd_fixture():
    pytest.importorskip("pxr.Usd")
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, 1.)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.)
    root = stage.DefinePrim("/World/AlternativeVessel", "Xform")
    root.CreateAttribute("lab:asset_type", Sdf.ValueTypeNames.String).Set("test_vessel")
    mesh = UsdGeom.Mesh.Define(stage, "/World/AlternativeVessel/Body").GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(mesh)
    UsdPhysics.CollisionAPI.Apply(mesh)
    UsdPhysics.MassAPI.Apply(mesh).CreateDensityAttr(.1)
    surface = UsdGeom.Mesh.Define(stage, "/World/OtherRobot/Finger").GetPrim()
    UsdPhysics.CollisionAPI.Apply(surface)
    UsdGeom.Subset.Define(stage, "/World/OtherRobot/Finger/subset")
    UsdPhysics.PrismaticJoint.Define(stage, "/World/OtherRobot/Joint")
    config = profile()
    config["bodies"][0]["asset_type"] = "test_vessel"
    config["surfaces"] = [{"paths": ["/World/OtherRobot/Finger"], "material": "finger"}]
    config["drives"][0]["joint_path"] = "/World/OtherRobot/Joint"
    return stage, config


def test_physics_applies_to_alternative_usd_paths_in_session_layer_only():
    from_px = pytest.importorskip("pxr.UsdPhysics")
    from pxr import UsdShade
    stage, config = usd_fixture()
    original = stage.GetRootLayer().ExportToString()
    report = apply_scene_physics(stage, config)
    assert stage.GetRootLayer().ExportToString() == original
    body = stage.GetPrimAtPath("/World/AlternativeVessel/Body")
    assert from_px.MassAPI(body).GetMassAttr().Get() == pytest.approx(.1)
    assert from_px.MassAPI(body).GetDensityAttr().Get() == 0
    for path in ("/World/OtherRobot/Finger", "/World/OtherRobot/Finger/subset"):
        material, _ = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(path)).ComputeBoundMaterial("physics")
        assert str(material.GetPath()) == "/World/PAOSPhysics/finger"
    assert report["bodies"][0]["before"]["density"] == pytest.approx(.1)


def test_missing_surface_does_not_partially_change_scene():
    stage, config = usd_fixture()
    config = deepcopy(config)
    config["surfaces"][0]["paths"] = ["/World/Missing"]
    original = stage.GetSessionLayer().ExportToString()
    with pytest.raises(ValueError, match="no active surface"):
        apply_scene_physics(stage, config)
    assert stage.GetSessionLayer().ExportToString() == original
