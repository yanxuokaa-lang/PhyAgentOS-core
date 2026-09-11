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
        if understanding.get("ambiguities"):
            raise ValueError("unambiguous scene understanding required")
        selected = request["entity_refs"]
        if not selected or len(set(selected)) != len(selected):
            raise ValueError("select distinct observed entities")
        if not set(selected) <= {e["entity_ref"] for e in understanding["entities"]}:
            raise ValueError("entity is not in the observation")
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
