"""Observed row goals and explicit execution identities, without motion authority."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
from uuid import uuid4

import numpy as np
from pick_place_workflow.layout import IDENTITY_KEYS

from .route_evidence import _artifact_path


def _matrix(value):
    a = np.asarray(value, dtype=float)
    if a.shape == (3, 4):
        a = np.vstack((a, [0, 0, 0, 1]))
    a = a.reshape(4, 4)
    if (not np.isfinite(a).all() or not np.allclose(a[3], [0, 0, 0, 1])
            or not np.allclose(a[:3, :3].T @ a[:3, :3], np.eye(3), atol=1e-5)
            or not np.isclose(np.linalg.det(a[:3, :3]), 1, atol=1e-5)):
        raise ValueError("invalid rigid calibration or object transform")
    return a


def bind_entities(entities, envelopes, objects, camera_to_world):
    """Require one unique overlapping execution OBB for each observed envelope.

    Conservative intersection permits partial visible surfaces but rejects a
    correspondence when any other execution object overlaps the observed box.
    No semantic label participates in execution identity selection.
    """
    result = {}
    for ref in entities:
        matches = [e for e in envelopes if e["entity_ref"] == ref]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous observed entity geometry")
        e = matches[0]
        low, high = np.asarray(e["min_xyz_m"]), np.asarray(e["max_xyz_m"])
        if low.shape != (3,) or high.shape != (3,) or not np.isfinite([low, high]).all() or np.any(low >= high):
            raise ValueError("invalid observed spatial envelope")
        corners = np.array([(*p, 1) for p in product(*zip(low, high))])
        world = corners @ camera_to_world.T
        candidates = []
        for obj in objects:
            pose = _matrix(obj["world_T_object"])
            local = world @ np.linalg.inv(pose).T
            half = np.asarray(obj["half_extents_m"], dtype=float)
            if half.shape != (3,) or not np.isfinite(half).all() or np.any(half <= 0):
                raise ValueError("invalid execution geometry")
            # AABB envelopes overestimate rotated visible surfaces; only accept
            # their center inside one OBB and an overlap on every local axis.
            center = local[:, :3].mean(axis=0)
            if (np.all(local[:, :3].min(axis=0) <= half)
                    and np.all(local[:, :3].max(axis=0) >= -half)):
                candidates.append((obj, bool(np.all(np.abs(center) <= half))))
        if len(candidates) != 1 or not candidates[0][1]:
            raise ValueError("execution entity correspondence is missing or ambiguous")
        result[ref] = deepcopy(candidates[0][0])
    if len({obj["entity_ref"] for obj in result.values()}) != len(result):
        raise ValueError("multiple observed entities bind one execution object")
    return result


class ObservedLayout:
    """Cache successful public understanding results and own no-motion layout artifacts."""

    def __init__(self, client, root, scene_source):
        self.client, self.root, self.source = client, root, scene_source
        self.observations = {}
        self.captures = {}
        self.layouts = {}

    def remember(self, arguments, result):
        if result.get("status") == "available":
            key = tuple(result[k] for k in IDENTITY_KEYS)
            if "captured_at" in result:
                self.captures[key] = result["captured_at"]
            else:
                self.observations[key] = deepcopy(result)

    def invoke(self, arguments):
        try:
            required = {*IDENTITY_KEYS, "ordered_entities", "axis", "max_age_ms"}
            if not isinstance(arguments, dict) or set(arguments) != required:
                raise ValueError("layout requires observation identities, ordered_entities, axis and max_age_ms")
            refs = arguments["ordered_entities"]
            age = arguments["max_age_ms"]
            if (not isinstance(refs, list) or len(refs) < 2
                    or any(not isinstance(r, str) or not r for r in refs)
                    or len(set(refs)) != len(refs)
                    or arguments["axis"] not in {"world+x", "world+y"}
                    or type(age) is not int or not 1 <= age <= 60000
                    or any(not isinstance(arguments[k], str) or not arguments[k] for k in IDENTITY_KEYS)):
                raise ValueError("invalid layout identities, order, axis or freshness")
            return self.resolve(arguments)
        except Exception as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": {"code": "layout_grounding_failed", "message": str(exc)}}

    def resolve(self, request):
        key = tuple(request[k] for k in IDENTITY_KEYS)
        observation = self.observations.get(key)
        if observation is None or observation.get("ambiguities"):
            raise ValueError("successful unambiguous scene understanding is required")
        if self.client.query("snapshot", {})["scene_revision"] != request["scene_revision"]:
            raise ValueError("layout scene is stale")
        calibration = json.loads(_artifact_path(self.root, request["calibration_ref"]).read_text())
        if calibration["camera_name"] != observation["frame"]["frame_id"]:
            raise ValueError("calibration frame mismatch")
        camera_to_world = np.linalg.inv(_matrix(calibration["extrinsic_cv"]))
        facts = self.source(request)
        if any(facts[k] != request[k] for k in IDENTITY_KEYS):
            raise ValueError("execution scene identity mismatch")
        # Observation artifacts, not request-supplied freshness, own capture time.
        captured = datetime.fromisoformat(self.captures[key].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - captured).total_seconds() * 1000
        if age < 0 or age > request["max_age_ms"]:
            raise ValueError("observation exceeds layout freshness window")
        envelopes = observation["spatial_envelopes"]
        if any(e["frame_id"] != calibration["camera_name"] or e["unit"] != "m" for e in envelopes):
            raise ValueError("spatial envelope frame or units mismatch")
        selected = request["ordered_entities"]
        if not set(selected) <= {e["entity_ref"] for e in observation["entities"]}:
            raise ValueError("layout entities are not in the observation")
        bound = bind_entities(selected, envelopes, facts["objects"], camera_to_world)
        axis = 0 if request["axis"] == "world+x" else 1
        measured_centers = []
        for ref in selected:
            envelope = next(e for e in envelopes if e["entity_ref"] == ref)
            center = (np.asarray(envelope["min_xyz_m"]) + np.asarray(envelope["max_xyz_m"])) / 2
            measured_centers.append((camera_to_world @ np.r_[center, 1])[:3])
        slots = sorted(p[axis] for p in measured_centers)
        row = float(np.mean([p[1-axis] for p in measured_centers]))
        token = uuid4().hex
        targets, bindings, replacements = [], [], []
        for index, (ref, obj) in enumerate(bound.items()):
            old = _matrix(obj["world_T_object"])
            target = old.copy()
            target[axis, 3], target[1-axis, 3] = slots[index], row
            destination = f"destination://layouts/{token}/{index}"
            bindings.append({"entity_ref": ref, "execution_entity_ref": obj["entity_ref"],
                             "actor_name": obj["actor_name"]})
            target_functional = target @ np.linalg.inv(old) @ _matrix(obj["world_T_functional_point"])
            obj.update(entity_ref=ref, target_ref=destination,
                       world_T_object_target=target.reshape(-1).tolist(),
                       world_T_functional_target=target_functional.reshape(-1).tolist())
            replacements.append(obj)
            targets.append({"entity_ref": ref, "destination_ref": destination,
                            "world_T_object_target": target.reshape(-1).tolist()})
        for a, b in zip(replacements, replacements[1:]):
            pa, pb = _matrix(a["world_T_object_target"]), _matrix(b["world_T_object_target"])
            ha = np.abs(pa[:3, :3]) @ np.asarray(a["half_extents_m"])
            hb = np.abs(pb[:3, :3]) @ np.asarray(b["half_extents_m"])
            if pb[axis, 3] - pa[axis, 3] <= ha[axis] + hb[axis]:
                raise ValueError("observed span cannot contain non-overlapping row targets")
        value = {**dict(zip(IDENTITY_KEYS, key)), "layout_ref": f"artifact://layouts/{token}",
                 "axis": request["axis"], "bindings": bindings, "targets": targets,
                 "scene_facts": {**facts, "objects": replacements}, "motion_authorized": False,
                 "captured_at": captured.isoformat(), "max_age_ms": request["max_age_ms"]}
        if self.client.query("snapshot", {})["scene_revision"] != request["scene_revision"]:
            raise ValueError("scene changed while resolving layout")
        directory = self.root / "layouts"
        directory.mkdir(exist_ok=True, parents=True)
        with (directory / f"{token}.json").open("x") as stream:
            json.dump(value, stream)
        self.layouts.update({t["destination_ref"]: value for t in targets})
        return {**{k: v for k, v in value.items() if k not in {"scene_facts", "bindings"}},
                "status": "available", "frame_id": "world", "unit": "m",
                "evidence_refs": [value["layout_ref"]],
                "entity_bindings": [{k: b[k] for k in ("entity_ref", "execution_entity_ref")} for b in bindings]}

    def scene_facts(self, request):
        layout = self.layouts.get(request["destination_ref"])
        if layout is None or any(layout[k] != request[k] for k in IDENTITY_KEYS):
            raise ValueError("destination must come from current observed layout")
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(layout["captured_at"])).total_seconds() * 1000
        if age < 0 or age > layout["max_age_ms"]:
            raise ValueError("layout expired before preparation")
        if self.client.query("snapshot", {})["scene_revision"] != layout["scene_revision"]:
            raise ValueError("layout is stale before preparation")
        self.client.query("bind_observed_entities", {"layout_ref": layout["layout_ref"]})
        return deepcopy(layout["scene_facts"])


class RememberUnderstanding:
    def __init__(self, endpoint, layout):
        self.endpoint, self.layout = endpoint, layout

    def invoke(self, arguments):
        result = self.endpoint.invoke(arguments)
        self.layout.remember(arguments, result)
        return result
