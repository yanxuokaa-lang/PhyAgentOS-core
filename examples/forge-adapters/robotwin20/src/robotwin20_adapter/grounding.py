"""Scene-bound identity receipts and explicit target transforms for persistent simulation."""

import json
from copy import deepcopy
from uuid import uuid4

import numpy as np
from pick_place_workflow.grounding import IDENTITY_KEYS

from .observed_binding import correspond, rigid_transform
from .route_evidence import _artifact_path


class Grounding:
    def __init__(self, client, root, scene_source):
        self.client, self.root, self.source = client, root, scene_source
        self.observations = {}
        self.understandings = {}
        self.bindings = {}
        self.targets = {}

    def remember(self, tool_id, result):
        if result.get("status") == "available":
            key = tuple(result[k] for k in IDENTITY_KEYS)
            cache = self.observations if tool_id == "scene.observe" else self.understandings
            cache[key] = deepcopy(result)

    def _current(self, identity):
        state = self.client.query("snapshot", {})
        if (state["scene_revision"] != identity["scene_revision"]
                or state.get("holding_state") != "empty"
                or state.get("scene_validity") != "action_driven"):
            raise ValueError("grounding requires the current idle action-driven scene")

    def _write(self, kind, value):
        ref = f"artifact://{kind}/{uuid4().hex}"
        path = self.root / (ref.removeprefix("artifact://") + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream)
        return ref

    def bind(self, request):
        key = tuple(request[k] for k in IDENTITY_KEYS)
        observed = self.observations[key]
        understanding = self.understandings[key]
        selected = request["entity_refs"]
        if not selected or len(set(selected)) != len(selected):
            raise ValueError("select distinct observed entities")
        if not set(selected) <= {e["entity_ref"] for e in understanding["entities"]}:
            raise ValueError("entity is not in the observation")
        selected_set = set(selected)
        blocking = [
            item for item in understanding.get("ambiguities", [])
            if item.get("code") != "object_shape_uncertain"
            and (not item.get("entity_refs") or selected_set.intersection(item.get("entity_refs", [])))
        ]
        if blocking:
            raise ValueError("selected entity has unresolved perception ambiguity")
        envelopes = {
            item.get("entity_ref"): item
            for item in understanding.get("spatial_envelopes", [])
            if isinstance(item, dict)
        }
        for entity_ref in selected:
            envelope = envelopes.get(entity_ref)
            if not envelope or envelope.get("unit") != "m":
                raise ValueError("selected entity lacks metric visual localization")
        self._current(request)
        calibration = json.loads(_artifact_path(self.root, request["calibration_ref"]).read_text())
        frame = understanding["frame"]["frame_id"]
        if frame != observed["frame"]["frame_id"] or frame != calibration["camera_name"]:
            raise ValueError("calibration frame mismatch")
        camera_to_world = np.linalg.inv(rigid_transform(calibration["extrinsic_cv"]))
        facts = self.source(request)
        if any(facts[k] != request[k] for k in IDENTITY_KEYS):
            raise ValueError("execution scene identity mismatch")
        objects = correspond(selected, understanding, facts["objects"], camera_to_world)
        objects = self._project_visual_geometry(selected, objects, understanding, camera_to_world)
        facts = deepcopy(facts)
        facts["objects"] = [objects.get(item["entity_ref"], item) for item in facts["objects"]]
        self._current(request)
        bindings = [{"entity_ref": ref, "execution_entity_ref": obj["entity_ref"],
                     "actor_name": obj["actor_name"]} for ref, obj in objects.items()]
        value = {**{k: request[k] for k in IDENTITY_KEYS}, "bindings": bindings,
                 "objects": objects, "scene_facts": facts, "frame_id": frame,
                 "world_T_observation": camera_to_world.reshape(-1).tolist(),
                 "captured_at": observed["captured_at"], "motion_authorized": False}
        ref = self._write("entity-bindings", value)
        self.bindings[ref] = value
        return {"status": "available", "binding_ref": ref, "motion_authorized": False,
                **{k: request[k] for k in IDENTITY_KEYS}, "frame_id": "world", "unit": "m",
                "observation_frame_id": frame, "world_T_observation": value["world_T_observation"],
                "captured_at": value["captured_at"], "validity": "current_action_driven_scene",
                "entities": [{"entity_ref": ref, "execution_entity_ref": obj["entity_ref"],
                              "world_T_object": obj["world_T_object"],
                              "half_extents_m": obj["half_extents_m"]} for ref, obj in objects.items()],
                "evidence_refs": [ref]}

    @staticmethod
    def _project_visual_geometry(selected, objects, understanding, camera_to_world):
        """Project visual evidence into route geometry; Runtime remains identity-only."""
        envelopes = {item["entity_ref"]: item for item in understanding.get("spatial_envelopes", [])}
        geometries = {
            item["entity_ref"]: item.get("descriptor", {})
            for item in understanding.get("derived_artifacts", [])
            if item.get("kind") == "object_geometry"
        }
        projected = {}
        for ref in selected:
            envelope, geometry = envelopes.get(ref), geometries.get(ref)
            if not envelope or not geometry:
                raise ValueError("selected entity lacks visual geometry evidence")
            low = np.asarray(envelope.get("min_xyz_m"), dtype=float)
            high = np.asarray(envelope.get("max_xyz_m"), dtype=float)
            dimensions = np.asarray(geometry.get("dimensions_m"), dtype=float)
            if (low.shape != (3,) or high.shape != (3,) or dimensions.shape != (3,)
                    or not np.isfinite([low, high, dimensions]).all()
                    or np.any(high <= low) or np.any(dimensions <= 0)):
                raise ValueError("visual geometry evidence is invalid")
            center_world = camera_to_world @ np.r_[((low + high) / 2.0), 1.0]
            visual_pose = np.eye(4)
            visual_pose[:3, :3] = camera_to_world[:3, :3]
            visual_pose[:3, 3] = center_world[:3]
            runtime = objects[ref]
            runtime_pose = rigid_transform(runtime["world_T_object"])
            functional_offset = np.linalg.inv(runtime_pose) @ rigid_transform(runtime["world_T_functional_point"])
            updated = deepcopy(runtime)
            updated["world_T_object"] = visual_pose.reshape(-1).tolist()
            updated["half_extents_m"] = (dimensions / 2.0).tolist()
            updated["world_T_functional_point"] = (visual_pose @ functional_offset).reshape(-1).tolist()
            projected[ref] = updated
        return projected

    def target(self, request):
        binding = self.bindings[request["binding_ref"]]
        self._current(binding)
        if request["unit"] != "m":
            raise ValueError("target unit must be metres")
        obj = binding["objects"][request["entity_ref"]]
        pose = rigid_transform(request["frame_T_object_target"])
        if request["frame_id"] == binding["frame_id"]:
            pose = rigid_transform(binding["world_T_observation"]) @ pose
        elif request["frame_id"] != "world":
            raise ValueError("target frame has no bound calibration")
        target = deepcopy(obj)
        target.update(entity_ref=request["entity_ref"], world_T_object_target=pose.reshape(-1).tolist(),
                      world_T_functional_target=(pose @ np.linalg.inv(rigid_transform(obj["world_T_object"]))
                                                 @ rigid_transform(obj["world_T_functional_point"])).reshape(-1).tolist())
        value = {**{k: binding[k] for k in IDENTITY_KEYS}, "binding_ref": request["binding_ref"],
                 "requested_pose": deepcopy(request), "object": target, "motion_authorized": False}
        evidence_ref = self._write("targets", value)
        destination = evidence_ref.replace("artifact://", "destination://", 1)
        self.targets[destination] = value
        return {"status": "available", "destination_ref": destination,
                "binding_ref": request["binding_ref"], "entity_ref": request["entity_ref"],
                **{k: binding[k] for k in IDENTITY_KEYS}, "frame_id": "world", "unit": "m",
                "world_T_object_target": target["world_T_object_target"],
                "evidence_refs": [request["binding_ref"], evidence_ref], "motion_authorized": False}

    def scene_facts(self, request):
        value = self.targets[request["destination_ref"]]
        if any(value[k] != request[k] for k in IDENTITY_KEYS):
            raise ValueError("target observation identity mismatch")
        if value["object"]["entity_ref"] != request["intent"]["entity_ref"]:
            raise ValueError("target belongs to a different entity")
        self._current(value)
        binding = self.bindings[value["binding_ref"]]
        self.client.query("bind_observed_entities", {"binding_ref": value["binding_ref"]})
        facts = deepcopy(binding["scene_facts"])
        obj = deepcopy(value["object"])
        obj["target_ref"] = request["destination_ref"]
        facts["objects"] = [obj]
        return facts


class GroundingEndpoint:
    def __init__(self, resolve):
        self.resolve = resolve

    def invoke(self, arguments):
        try:
            return self.resolve(arguments)
        except (KeyError, ValueError, TypeError, OSError) as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": {"code": "grounding_unavailable", "message": str(exc)}}


class RememberObservation:
    def __init__(self, endpoint, grounding, tool_id):
        self.endpoint, self.grounding, self.tool_id = endpoint, grounding, tool_id

    def invoke(self, arguments):
        result = self.endpoint.invoke(arguments)
        self.grounding.remember(self.tool_id, result)
        return result
