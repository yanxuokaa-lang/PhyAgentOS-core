"""No-motion deployment checks; no Isaac execution or route claim."""
import json
from pathlib import Path

import numpy as np
import pytest

from isaacsim_lab.profile import LabUtopiaProfile

CONFIGS = Path(__file__).parents[1] / "configs"
SOURCE_ROBOT = Path("/home/yanxu/LabUtopia/assets/robots/ridgeback_franka.usd")


def stages():
    pytest.importorskip("pxr")
    from pxr import Usd

    if not SOURCE_ROBOT.exists():
        pytest.skip("requires deployed LabUtopia robot asset")
    return Usd.Stage.Open(str(SOURCE_ROBOT)), Usd.Stage.Open(str(CONFIGS / "labutopia-ridgebase-elevated.usda"))


def test_elevated_robot_preserves_chassis_and_all_arm_joint_anchors():
    original, elevated = stages()
    from pxr import UsdGeom, UsdPhysics
    assert UsdGeom.GetStageMetersPerUnit(elevated) == 1.
    assert UsdGeom.GetStageUpAxis(elevated) == UsdGeom.Tokens.z
    names = [*[f"panda_link{i}" for i in range(8)], "panda_hand", "panda_leftfinger", "panda_rightfinger", "endeffector"]
    for name in names + ["base_link", "arm_mount_link", "dummy_base_x", "dummy_base_y", "world", "front_laser", "rear_laser"]:
        old = UsdGeom.Xformable(original.GetPrimAtPath("/panda_mobile/" + name)).ComputeLocalToWorldTransform(0.)
        new_prim = elevated.GetPrimAtPath("/panda_mobile/" + name)
        new = UsdGeom.Xformable(new_prim).ComputeLocalToWorldTransform(0.)
        delta = np.array(new) - np.array(old)
        expected = np.zeros((4, 4))
        if name in names:
            expected[3, 2] = .43
        assert delta == pytest.approx(expected, abs=1e-12)
        assert tuple(new_prim.GetAttribute("xformOp:scale").Get()) == (1., 1., 1.)
    joints = [p for p in elevated.Traverse() if p.IsA(UsdPhysics.Joint)]
    assert joints
    for prim in joints:
        joint = UsdPhysics.Joint(prim)
        old_joint = UsdPhysics.Joint(original.GetPrimAtPath(prim.GetPath()))
        new_anchors, old_anchors = [], []
        for body_rel, pos_attr in [("Body0", "LocalPos0"), ("Body1", "LocalPos1")]:
            for scene, item, anchors in [(elevated, joint, new_anchors), (original, old_joint, old_anchors)]:
                targets = getattr(item, "Get" + body_rel + "Rel")().GetTargets()
                pos = getattr(item, "Get" + pos_attr + "Attr")().Get()
                anchors.append(np.array(UsdGeom.Xformable(scene.GetPrimAtPath(targets[0])).ComputeLocalToWorldTransform(0.).Transform(pos)) if targets else np.array(pos))
        assert new_anchors[0] - new_anchors[1] == pytest.approx(old_anchors[0] - old_anchors[1], abs=5e-8)


def test_column_has_collision_and_matches_mount_mass_properties():
    _, elevated = stages()
    from pxr import UsdGeom, UsdPhysics
    mount = elevated.GetPrimAtPath("/panda_mobile/arm_mount_link")
    column = elevated.GetPrimAtPath(mount.GetPath().AppendChild("elevation_column"))
    assert column.HasAPI(UsdPhysics.CollisionAPI)
    assert UsdPhysics.CollisionAPI(column).GetCollisionEnabledAttr().Get()
    bounds = UsdGeom.BBoxCache(0., ["default"]).ComputeWorldBound(column).ComputeAlignedRange()
    assert np.array(bounds.GetMin()) == pytest.approx([.24, -.06, .28], abs=1e-6)
    assert np.array(bounds.GetMax()) == pytest.approx([.36, .06, .71], abs=1e-6)
    mass = UsdPhysics.MassAPI(mount)
    assert mass.GetMassAttr().Get() == pytest.approx(6.)
    assert tuple(mass.GetCenterOfMassAttr().Get()) == pytest.approx([.3, 0., .215])
    assert tuple(mass.GetDiagonalInertiaAttr().Get()) == pytest.approx([.09965, .09965, .0144])


def test_elevated_profile_retains_motion_thresholds():
    yaml = pytest.importorskip("yaml")
    station = yaml.safe_load((CONFIGS / "labutopia-ridgebase-station.yaml").read_text())
    assert station["robot"]["base_position"] == [-1.12, .18, .01]
    profile = LabUtopiaProfile.from_json(CONFIGS / "labutopia-ridgebase.json")
    assert str(profile.robot_usd_path) == station["robot"]["usd_asset"]
    assert profile.robot_usd_path.name == "labutopia-ridgebase-elevated.usda"
    new_motion = json.loads(profile.motion_config_path.read_text())
    old_motion = json.loads((CONFIGS / "labutopia-oracle-motion.json").read_text())
    assert new_motion.pop("mount_collision_paths") == old_motion.pop("mount_collision_paths") + ["/World/Ridgebase/arm_mount_link/elevation_column"]
    assert new_motion == old_motion


def test_elevated_scene_removes_legacy_arm():
    stages()
    from pxr import Usd

    profile = LabUtopiaProfile.from_json(CONFIGS / "labutopia-ridgebase.json")
    profile.validate_paths()
    scene = Usd.Stage.Open(str(profile.scene_usd_path))
    assert not scene.GetPrimAtPath("/World/Franka").IsActive()
