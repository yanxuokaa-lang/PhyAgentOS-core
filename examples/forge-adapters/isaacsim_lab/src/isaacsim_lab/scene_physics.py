"""Isaac-private scene physics, authored once before reset/capture.

Simulation assumptions are explicit deployment configuration, not inferred
laboratory measurements. Session-layer opinions never modify source assets.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


def load_physics_config(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("assumptions"):
        raise ValueError("scene physics requires documented simulation assumptions")
    materials = value["materials"]
    for material in materials.values():
        for key in ("static_friction", "dynamic_friction", "restitution"):
            number = material[key]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
                raise ValueError(f"invalid physics material {key}")
        if material["static_friction"] < material["dynamic_friction"] or material["restitution"] > 1:
            raise ValueError("invalid friction ordering or restitution")
    for body in value["bodies"]:
        mass = body["mass_kg"]
        if isinstance(mass, bool) or not isinstance(mass, (float, int)) or not math.isfinite(mass) or mass <= 0:
            raise ValueError("body mass_kg must be finite and positive")
        if not body.get("asset_type") or body["material"] not in materials:
            raise ValueError("body requires asset_type and known material")
        for key in ("hull_vertex_limit", "max_convex_hulls"):
            if type(body[key]) is not int or body[key] < 4:
                raise ValueError(f"invalid convex decomposition {key}")
    for surface in value["surfaces"]:
        if surface["material"] not in materials or not surface["paths"]:
            raise ValueError("surface requires paths and known material")
    for drive in value["drives"]:
        for key in ("max_force_n", "max_velocity_m_s"):
            number = drive[key]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number <= 0:
                raise ValueError(f"invalid drive {key}")
    return value


def apply_scene_physics(stage, config):
    """Resolve every target before authoring; call only before World.reset()."""
    from pxr import PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    if UsdGeom.GetStageMetersPerUnit(stage) != 1. or UsdPhysics.GetStageKilogramsPerUnit(stage) != 1.:
        raise ValueError("physics profile requires metre/kilogram stage units")

    def colliders(root):
        return [prim for prim in Usd.PrimRange(root) if prim.HasAPI(UsdPhysics.CollisionAPI)
                and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()]

    bodies, surfaces, drives = [], [], []
    for spec in config["bodies"]:
        roots = [p for p in stage.Traverse() if p.GetAttribute("lab:asset_type").Get() == spec["asset_type"]]
        if not roots:
            raise ValueError(f"no bodies for asset_type {spec['asset_type']}")
        for root in roots:
            rigid = [p for p in Usd.PrimRange(root) if p.HasAPI(UsdPhysics.RigidBodyAPI)]
            shapes = colliders(root)
            if len(rigid) != 1 or not shapes:
                raise ValueError(f"expected one rigid body with active colliders under {root.GetPath()}")
            bodies.append((rigid[0], shapes, spec))
    for spec in config["surfaces"]:
        for path in spec["paths"]:
            root = stage.GetPrimAtPath(path)
            shapes = colliders(root) if root else []
            if not shapes:
                raise ValueError(f"no active surface colliders under {path}")
            surfaces.append((shapes, spec))
    for spec in config["drives"]:
        prim = stage.GetPrimAtPath(spec["joint_path"])
        if not prim or not prim.IsA(UsdPhysics.PrismaticJoint):
            raise ValueError(f"missing prismatic drive {spec['joint_path']}")
        drives.append((prim, spec))

    report = {"assumptions": config["assumptions"], "scope": "simulation_configuration",
              "bodies": [], "surfaces": [], "drives": [], "source_assets_modified": False}
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        materials = {}
        for name, spec in config["materials"].items():
            material = UsdShade.Material.Define(stage, f"/World/PAOSPhysics/{name}")
            physics = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
            physics.CreateStaticFrictionAttr(spec["static_friction"])
            physics.CreateDynamicFrictionAttr(spec["dynamic_friction"])
            physics.CreateRestitutionAttr(spec["restitution"])
            materials[name] = material

        def bind(shapes, name):
            # Bind collision prims and their subsets, so an inherited render
            # subset cannot silently select a different physical material.
            for shape in shapes:
                for prim in (shape, *[p for p in shape.GetChildren() if p.IsA(UsdGeom.Subset)]):
                    UsdShade.MaterialBindingAPI.Apply(prim).Bind(
                        materials[name], bindingStrength=UsdShade.Tokens.strongerThanDescendants,
                        materialPurpose="physics")

        for rigid, shapes, spec in bodies:
            before = {name: rigid.GetAttribute("physics:" + name).Get() for name in ("mass", "density")}
            mass = UsdPhysics.MassAPI.Apply(rigid)
            mass.CreateMassAttr(spec["mass_kg"])
            mass.CreateDensityAttr(0.)
            for shape in shapes:
                UsdPhysics.MeshCollisionAPI.Apply(shape).CreateApproximationAttr("convexDecomposition")
                convex = PhysxSchema.PhysxConvexDecompositionCollisionAPI.Apply(shape)
                convex.CreateHullVertexLimitAttr(spec["hull_vertex_limit"])
                convex.CreateMaxConvexHullsAttr(spec["max_convex_hulls"])
            bind(shapes, spec["material"])
            report["bodies"].append({"path": str(rigid.GetPath()), "before": before,
                                     "configured_mass_kg": spec["mass_kg"],
                                     "colliders": [str(p.GetPath()) for p in shapes], "material": spec["material"]})
        for shapes, spec in surfaces:
            bind(shapes, spec["material"])
            report["surfaces"].append({"colliders": [str(p.GetPath()) for p in shapes], "material": spec["material"]})
        for prim, spec in drives:
            UsdPhysics.DriveAPI.Apply(prim, "linear").CreateMaxForceAttr(spec["max_force_n"])
            prim.CreateAttribute("physxJoint:maxJointVelocity", Sdf.ValueTypeNames.Float).Set(spec["max_velocity_m_s"])
            report["drives"].append(dict(spec))
    report["authored_materials"] = config["materials"]
    return report


def read_runtime_physics(report, *, rigid_factory=None):
    """Measure mass, COM and inertia after reset; not a grasp-success verdict."""
    if rigid_factory is None:
        from isaacsim.core.prims import RigidPrim
        def rigid_factory(path):
            return RigidPrim(prim_paths_expr=path)
    result = {**report, "bodies": []}
    for body in report["bodies"]:
        view = rigid_factory(body["path"])
        view.initialize()
        mass = float(np.asarray(view.get_masses()).reshape(-1)[0])
        inertia = np.asarray(view.get_inertias()).reshape(3, 3)
        com, orientation = view.get_coms()
        if (not math.isfinite(mass) or mass <= 0 or not np.isfinite(inertia).all()
                or not np.allclose(inertia, inertia.T) or np.min(np.linalg.eigvalsh(inertia)) <= 0
                or not np.isfinite(com).all() or not np.isfinite(orientation).all()):
            raise ValueError(f"invalid runtime mass/inertia/COM: {body['path']}")
        if not math.isclose(mass, body["configured_mass_kg"], rel_tol=1e-4):
            raise ValueError(f"runtime mass differs from configured mass: {body['path']}")
        result["bodies"].append({**body, "measured_mass_kg": mass,
                                 "measured_inertia_kg_m2": inertia.tolist(),
                                 "measured_com_local_m": np.asarray(com).reshape(3).tolist(),
                                 "measured_com_orientation_wxyz": np.asarray(orientation).reshape(4).tolist()})
    result["scope"] = "initialized_physics_readback; no controller motion"
    return result
