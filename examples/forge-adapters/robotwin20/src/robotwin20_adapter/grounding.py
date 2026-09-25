"""Scene-bound identity receipts and explicit target transforms for persistent simulation."""

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from uuid import uuid4

import numpy as np
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError
from pick_place_workflow.grounding import IDENTITY_KEYS

from .observed_binding import correspond, rigid_transform
from .observed_support import SupportEstimationPolicy, estimate_support
from .route_evidence import _artifact_path

_DEFERRED_BINDING_AMBIGUITIES = {
    "object_shape_uncertain",
    "metric_3d_unavailable",
    "metric_geometry_unavailable",
    "NO_RELIABLE_METRIC_EXTENTS",
}


class Grounding:
    def __init__(self, client, root, scene_source, *, support_policy=None, collision_policy=None,
                 goal_source="observation_owned"):
        self.client, self.root, self.source = client, root, scene_source
        self.support_policy = support_policy or SupportEstimationPolicy()
        self.collision_policy = collision_policy
        self.goal_source = goal_source
        self.observations = {}
        self.understandings = {}
        self.bindings = {}
        self.targets = {}
        self.last_diagnostics = None

    def _reject(self, message, *, stage, **details):
        self.last_diagnostics = {"stage": stage, "message": message, **details}
        raise ValueError(message)

    def remember(self, tool_id, result):
        if result.get("status") == "available":
            key = tuple(result[k] for k in IDENTITY_KEYS)
            cache = self.observations if tool_id == "scene.observe" else self.understandings
            cache[key] = deepcopy(result)

    def _current(self, identity, *, deadline=None):
        try:
            kwargs = {} if deadline is None else {"timeout_s": deadline.remaining("grounding_snapshot")}
            state = self.client.query("snapshot", {}, **kwargs)
        except TimeoutError:
            raise
        except Exception as exc:
            self._reject(
                "current scene snapshot is unavailable",
                stage="current_scene",
                error_type=type(exc).__name__,
                expected_scene_revision=identity.get("scene_revision"),
            )
        if not isinstance(state, dict):
            self._reject(
                "current scene snapshot has invalid shape",
                stage="current_scene",
                expected_scene_revision=identity.get("scene_revision"),
                actual_type=type(state).__name__,
            )
        expected = {
            "scene_revision": identity.get("scene_revision"),
            "holding_state": "empty",
            "scene_validity": "action_driven",
        }
        actual = {key: state.get(key) for key in expected}
        if actual != expected:
            self._reject(
                "grounding requires the current idle action-driven scene",
                stage="current_scene",
                expected=expected,
                actual=actual,
            )

    def _write(self, kind, value):
        ref = f"artifact://{kind}/{uuid4().hex}"
        path = self.root / (ref.removeprefix("artifact://") + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream)
        return ref

    def bind(self, request):
        self.last_diagnostics = None
        if not isinstance(request, Mapping):
            self._reject(
                "scene binding request must be an object",
                stage="input_validation",
                actual_type=type(request).__name__,
            )
        missing = [name for name in (*IDENTITY_KEYS, "entity_refs") if name not in request]
        if missing:
            self._reject(
                "scene binding request is missing required fields",
                stage="input_validation",
                missing_fields=missing,
            )
        key = tuple(request[k] for k in IDENTITY_KEYS)
        try:
            observed = self.observations[key]
        except KeyError:
            self._reject(
                "scene observation evidence is unavailable",
                stage="observation_evidence",
                identity={name: request.get(name) for name in IDENTITY_KEYS},
            )
        try:
            understanding = self.understandings[key]
        except KeyError:
            self._reject(
                "scene understanding evidence is unavailable",
                stage="understanding_evidence",
                identity={name: request.get(name) for name in IDENTITY_KEYS},
            )
        selected = request["entity_refs"]
        if not isinstance(selected, list) or any(not isinstance(ref, str) or not ref for ref in selected):
            self._reject(
                "entity_refs must be a non-empty array of references",
                stage="input_validation",
                selected=selected,
            )
        if not selected or len(set(selected)) != len(selected):
            self._reject("select distinct observed entities", stage="entity_selection", selected=selected)
        if not set(selected) <= {e["entity_ref"] for e in understanding["entities"]}:
            self._reject(
                "entity is not in the observation",
                stage="entity_selection",
                selected=selected,
                observed_entities=[e.get("entity_ref") for e in understanding["entities"]],
            )
        selected_set = set(selected)
        envelopes = {}
        for item in understanding.get("spatial_envelopes", []):
            if not isinstance(item, Mapping) or not item.get("entity_ref"):
                continue
            if item["entity_ref"] in envelopes:
                self._reject(
                    "selected scene contains duplicate metric localizations",
                    stage="metric_localization",
                    entity_ref=item["entity_ref"],
                )
            envelopes[item["entity_ref"]] = item
        blocking = []
        deferred = []
        for item in understanding.get("ambiguities", []):
            refs = item.get("entity_refs", [])
            applies = not refs or selected_set.intersection(refs)
            if not applies:
                continue
            code = item.get("code")
            if code in _DEFERRED_BINDING_AMBIGUITIES:
                deferred.append(item)
                continue
            blocking.append(item)
        if blocking:
            self._reject(
                "selected entity has unresolved perception ambiguity",
                stage="ambiguity_admission",
                selected_entities=selected,
                blocking_ambiguities=[
                    {
                        "code": item.get("code"),
                        "entity_refs": item.get("entity_refs", []),
                        "message": item.get("message"),
                    }
                    for item in blocking
                ],
                deferred_ambiguities=[
                    {"code": item.get("code"), "entity_refs": item.get("entity_refs", [])}
                    for item in deferred
                ],
            )
        for entity_ref in selected:
            envelope = envelopes.get(entity_ref)
            if not envelope or envelope.get("unit") != "m":
                self._reject(
                    "selected entity lacks metric visual localization",
                    stage="metric_localization",
                    entity_ref=entity_ref,
                    available_envelopes=sorted(envelopes),
                )
            if envelope.get("frame_id") != understanding["frame"]["frame_id"]:
                self._reject(
                    "selected entity metric localization frame mismatch",
                    stage="metric_localization",
                    entity_ref=entity_ref,
                    expected_frame=understanding["frame"]["frame_id"],
                    actual_frame=envelope.get("frame_id"),
                )
        self._current(request)
        try:
            calibration = json.loads(_artifact_path(self.root, request["calibration_ref"]).read_text())
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._reject(
                "calibration artifact is unavailable or invalid",
                stage="calibration",
                calibration_ref=request.get("calibration_ref"),
                error_type=type(exc).__name__,
            )
        frame = understanding["frame"]["frame_id"]
        calibration_frame = calibration.get("camera_name") if isinstance(calibration, dict) else None
        if frame != observed["frame"]["frame_id"] or frame != calibration_frame:
            self._reject(
                "calibration frame mismatch",
                stage="calibration",
                observation_frame=observed["frame"]["frame_id"],
                understanding_frame=frame,
                calibration_frame=calibration_frame,
            )
        try:
            camera_to_world = np.linalg.inv(rigid_transform(calibration["extrinsic_cv"]))
        except (KeyError, TypeError, ValueError, np.linalg.LinAlgError) as exc:
            self._reject(
                "calibration transform is invalid",
                stage="calibration",
                calibration_ref=request.get("calibration_ref"),
                error_type=type(exc).__name__,
            )
        try:
            facts = self.source(request)
        except Exception as exc:
            self._reject(
                "execution scene facts are unavailable",
                stage="execution_identity",
                error_type=type(exc).__name__,
            )
        if not isinstance(facts, dict):
            self._reject(
                "execution scene facts have invalid shape",
                stage="execution_identity",
                actual_type=type(facts).__name__,
            )
        actual_identity = {key: facts.get(key) for key in IDENTITY_KEYS}
        expected_identity = {key: request.get(key) for key in IDENTITY_KEYS}
        if actual_identity != expected_identity:
            self._reject(
                "execution scene identity mismatch",
                stage="execution_identity",
                expected=expected_identity,
                actual=actual_identity,
            )
        try:
            objects = correspond(selected, understanding, facts["objects"], camera_to_world)
        except (KeyError, TypeError, ValueError) as exc:
            self._reject(
                "execution correspondence is unavailable or ambiguous",
                stage="execution_correspondence",
                selected_entities=selected,
                error_type=type(exc).__name__,
                reason=str(exc),
            )
        objects = self._project_visual_geometry(selected, objects, understanding, camera_to_world)
        facts = deepcopy(facts)
        # Keep captured execution poses intact for Runtime drift checks. Visual
        # route geometry lives in objects, in its own observation-derived frame.
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

    def _project_visual_geometry(self, selected, objects, understanding, camera_to_world):
        """Project visual evidence into route geometry; Runtime remains identity-only."""
        envelopes = {
            item["entity_ref"]: item
            for item in understanding.get("spatial_envelopes", [])
            if isinstance(item, Mapping) and item.get("entity_ref")
        }
        projected = {}
        for ref in selected:
            envelope = envelopes.get(ref)
            if not envelope:
                self._reject(
                    "selected entity lacks visual metric localization",
                    stage="metric_localization",
                    entity_ref=ref,
                )
            if envelope.get("unit") != "m" or envelope.get("frame_id") != understanding["frame"]["frame_id"]:
                self._reject(
                    "visual metric envelope frame or unit is invalid",
                    stage="metric_localization",
                    entity_ref=ref,
                    expected_frame=understanding["frame"]["frame_id"],
                    actual_frame=envelope.get("frame_id"),
                    actual_unit=envelope.get("unit"),
                )
            low = np.asarray(envelope.get("min_xyz_m"), dtype=float)
            high = np.asarray(envelope.get("max_xyz_m"), dtype=float)
            geometry_items = [
                item for item in understanding.get("derived_artifacts", [])
                if isinstance(item, Mapping)
                and item.get("kind") == "object_geometry"
                and item.get("entity_ref") == ref
            ]
            if len(geometry_items) > 1:
                self._reject(
                    "visual object geometry is ambiguous",
                    stage="visual_geometry",
                    entity_ref=ref,
                    artifact_count=len(geometry_items),
                )
            geometry_present = bool(geometry_items)
            geometry = geometry_items[0].get("descriptor") if geometry_present else None
            if geometry_present and not isinstance(geometry, dict):
                self._reject(
                    "visual object geometry descriptor is invalid",
                    stage="visual_geometry",
                    entity_ref=ref,
                )
            # A metric envelope is sufficient for identity binding and gives a
            # conservative visual extent when the optional shape estimator did
            # not emit object_geometry. Grasp/prepare must still qualify shape
            # and candidate readiness before any Action.
            dimensions = (
                np.asarray(geometry.get("dimensions_m"), dtype=float)
                if geometry_present
                else high - low
            )
            if (low.shape != (3,) or high.shape != (3,) or dimensions.shape != (3,)
                    or not np.isfinite([low, high, dimensions]).all()
                    or np.any(high <= low) or np.any(dimensions <= 0)):
                self._reject(
                    "visual geometry evidence is invalid",
                    stage="visual_geometry",
                    entity_ref=ref,
                    geometry_artifact_present=geometry_present,
                )
            center_world = camera_to_world @ np.r_[((low + high) / 2.0), 1.0]
            visual_pose = np.eye(4)
            visual_pose[:3, :3] = camera_to_world[:3, :3]
            visual_pose[:3, 3] = center_world[:3]
            model_frame = "observed-envelope"
            if geometry_present and geometry.get("shape_class") == "box_envelope" and geometry.get("orientation_reliable") is False:
                clouds = [a for a in understanding.get("derived_artifacts", [])
                          if a.get("kind") == "object_point_cloud" and a.get("entity_ref") == ref]
                if len(clouds) > 1:
                    self._reject("observed object point cloud is ambiguous", stage="visual_geometry", entity_ref=ref)
                if clouds:
                    cloud = clouds[0]
                    if (any(cloud.get(k) != understanding[k] for k in IDENTITY_KEYS)
                            or cloud.get("frame_id") != understanding["frame"]["frame_id"]):
                        self._reject("observed object cloud lineage differs from binding", stage="visual_geometry", entity_ref=ref)
                    points = np.load(_artifact_path(self.root, cloud["artifact_ref"] + ".npy"), allow_pickle=False)
                    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0 or not np.isfinite(points).all():
                        self._reject("observed object point cloud is invalid", stage="visual_geometry", entity_ref=ref)
                    # Bound measured points after calibration, not the empty
                    # corners of a camera-axis box. Retain every point and any
                    # producer-supplied envelope padding, projected into world.
                    cloud_low, cloud_high = points.min(axis=0), points.max(axis=0)
                    padding = np.maximum.reduce([np.zeros(3), cloud_low - low, high - cloud_high,
                                                 (dimensions - (cloud_high - cloud_low)) / 2])
                    world = points @ camera_to_world[:3, :3].T + camera_to_world[:3, 3]
                    padding_world = np.abs(camera_to_world[:3, :3]) @ padding
                    world_low = world.min(axis=0) - padding_world
                    world_high = world.max(axis=0) + padding_world
                    dimensions = np.maximum(world_high - world_low, 1e-4)
                    visual_pose = np.eye(4)
                    visual_pose[:3, 3] = (world_low + world_high) / 2
                    model_frame = "observed-envelope/world"
            runtime = objects[ref]
            updated = deepcopy(runtime)
            # This is an estimated envelope frame, not the physical actor frame.
            # Its origin is the observed centroid; no hidden functional point is used.
            updated["object_frame_id"] = f"{model_frame}/{ref.removeprefix('entity://')}"
            updated["world_T_object"] = visual_pose.reshape(-1).tolist()
            updated["half_extents_m"] = (dimensions / 2.0).tolist()
            updated["world_T_functional_point"] = visual_pose.reshape(-1).tolist()
            updated["functional_point_id"] = 0
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

    def activate_observed_entities(self, request: Mapping[str, Any]) -> str:
        """Synchronize one persisted semantic binding to the Runtime worker."""

        targets = request.get("targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError("observed entity activation requires grasp targets")
        entity_refs = {
            item.get("entity_ref") for item in targets if isinstance(item, Mapping)
        }
        if len(entity_refs) != len(targets) or None in entity_refs:
            raise ValueError("observed entity activation targets are invalid")
        matches = [
            (reference, binding)
            for reference, binding in self.bindings.items()
            if all(binding.get(key) == request.get(key) for key in IDENTITY_KEYS)
            and entity_refs <= set(binding.get("objects", {}))
        ]
        if len(matches) != 1:
            raise ValueError("current observed entity binding is absent or ambiguous")
        reference, binding = matches[0]
        self._current(binding)
        self.client.query("bind_observed_entities", {"binding_ref": reference})
        return reference

    def scene_facts(self, request, *, deadline=None):
        value = self.targets.get(request["destination_ref"])
        if value is None:
            if self.goal_source != "benchmark_task_definition":
                raise ValueError("destination is not an observation-owned target")
            value = self._benchmark_goal_target(request, deadline=deadline)
        if any(value[k] != request[k] for k in IDENTITY_KEYS):
            raise ValueError("target observation identity mismatch")
        if value["object"]["entity_ref"] != request["intent"]["entity_ref"]:
            raise ValueError("target belongs to a different entity")
        self._current(value, deadline=deadline)
        binding = self.bindings[value["binding_ref"]]
        kwargs = {} if deadline is None else {"timeout_s": deadline.remaining("bind_observed_entities")}
        self.client.query("bind_observed_entities", {"binding_ref": value["binding_ref"]}, **kwargs)
        facts = deepcopy(binding["scene_facts"])
        obj = deepcopy(value["object"])
        obj["target_ref"] = request["destination_ref"]
        # Captured actor geometry is private drift/identity evidence. Every
        # planning obstacle must have its own observation-derived model.
        by_execution = {item["entity_ref"]: (ref, item) for ref, item in binding["objects"].items()}
        missing = [item["entity_ref"] for item in facts["objects"] if item["entity_ref"] not in by_execution]
        if missing:
            raise PreparationProviderError("observed_collision_coverage_incomplete",
                                           "observed collision coverage is incomplete; bind all observed obstacles")
        facts["objects"] = []
        for ref, model in by_execution.values():
            item = deepcopy(model)
            item["entity_ref"] = ref
            facts["objects"].append(obj if ref == obj["entity_ref"] else item)
        facts["geometry_source"] = "observation"
        if self.collision_policy is not None:
            identity = tuple(binding[k] for k in IDENTITY_KEYS)
            observed, understanding = self.observations[identity], self.understandings[identity]
            masks = [a for a in understanding.get("derived_artifacts", [])
                     if a.get("kind") == "instance_mask" and a.get("entity_ref") == obj["entity_ref"]]
            depths = [a for a in observed.get("artifacts", []) if a.get("kind") == "depth"]
            if len(masks) != 1 or len(depths) != 1:
                raise PreparationProviderError("observed_collision_unavailable", "one target mask and complete scene depth are required")
            mask = masks[0]
            if any(mask.get(k) != binding[k] for k in IDENTITY_KEYS) or mask.get("frame_id") != binding["frame_id"]:
                raise PreparationProviderError("observed_collision_unavailable", "target mask lineage differs from binding")
            facts["observed_collision"] = {
                **{k: binding[k] for k in IDENTITY_KEYS}, "frame_id": binding["frame_id"],
                "world_T_camera": binding["world_T_observation"], "depth_ref": depths[0]["ref"],
                "target_mask_ref": mask["artifact_ref"], "target_entity_ref": obj["entity_ref"],
                "policy": self.collision_policy.to_dict(), "visibility_scope": "observed_only",
                "unknown_space_policy": "report_for_agent_recovery",
            }
        support = self._observed_support(binding)
        if support is not None:
            facts["support_surface"] = support
        return facts

    def oracle_scene_facts(self, request, *, deadline=None):
        """Bind simulator actor geometry to Agent-selected observed identities."""
        value = self.targets.get(request["destination_ref"])
        if value is None:
            value = self._benchmark_goal_target(request, deadline=deadline)
        if any(value[key] != request[key] for key in IDENTITY_KEYS):
            raise ValueError("target observation identity mismatch")
        target_entity = request["intent"]["entity_ref"]
        if value["object"]["entity_ref"] != target_entity:
            raise ValueError("target belongs to a different entity")
        self._current(value, deadline=deadline)
        binding = self.bindings[value["binding_ref"]]
        kwargs = (
            {}
            if deadline is None
            else {"timeout_s": deadline.remaining("bind_observed_entities")}
        )
        self.client.query(
            "bind_observed_entities", {"binding_ref": value["binding_ref"]}, **kwargs
        )
        facts = deepcopy(binding["scene_facts"])
        originals = {item["entity_ref"]: item for item in facts["objects"]}
        observed_by_execution = {
            model["entity_ref"]: observed_ref
            for observed_ref, model in binding["objects"].items()
        }
        missing = sorted(set(originals) - set(observed_by_execution))
        if missing:
            raise PreparationProviderError(
                "oracle_collision_coverage_incomplete",
                "oracle route requires every execution object to have an observed identity binding",
            )
        target_world_object = rigid_transform(value["object"]["world_T_object_target"])
        projected = []
        for execution_ref, original in originals.items():
            observed_ref = observed_by_execution[execution_ref]
            item = deepcopy(original)
            item["entity_ref"] = observed_ref
            if observed_ref == target_entity:
                world_object = rigid_transform(original["world_T_object"])
                world_functional = rigid_transform(original["world_T_functional_point"])
                object_functional = np.linalg.inv(world_object) @ world_functional
                item.update(
                    target_ref=request["destination_ref"],
                    world_T_object_target=target_world_object.reshape(-1).tolist(),
                    world_T_functional_target=(
                        target_world_object @ object_functional
                    ).reshape(-1).tolist(),
                )
            projected.append(item)
        facts["objects"] = projected
        facts["geometry_source"] = "oracle_actor"
        facts.pop("support_surface", None)
        facts.pop("observed_collision", None)
        return facts

    def _benchmark_goal_target(self, request, *, deadline=None):
        """Resolve one Runtime-owned benchmark destination through current binding."""

        target_entity = request.get("intent", {}).get("entity_ref")
        destination_ref = request.get("destination_ref")
        if not isinstance(target_entity, str) or not isinstance(destination_ref, str):
            raise ValueError("benchmark target request is incomplete")
        matches = [
            (reference, binding)
            for reference, binding in self.bindings.items()
            if all(binding.get(key) == request.get(key) for key in IDENTITY_KEYS)
            and target_entity in binding.get("objects", {})
        ]
        if len(matches) != 1:
            raise ValueError("benchmark target binding is absent or ambiguous")
        binding_ref, binding = matches[0]
        observed_object = binding["objects"][target_entity]
        execution_entity = observed_object.get("entity_ref")
        kwargs = (
            {}
            if deadline is None
            else {"timeout_s": deadline.remaining("task_goal_facts")}
        )
        goal_facts = self.client.query("task_goal_facts", {}, **kwargs)
        if (
            not isinstance(goal_facts, Mapping)
            or goal_facts.get("status") != "available"
            or goal_facts.get("geometry_source") != "benchmark_task_definition"
        ):
            raise ValueError("benchmark goal facts are unavailable")
        goals = goal_facts.get("goals")
        if not isinstance(goals, list):
            raise ValueError("benchmark goals are invalid")
        goal_matches = [
            goal
            for goal in goals
            if isinstance(goal, Mapping)
            and goal.get("destination_ref") == destination_ref
            and goal.get("execution_entity_ref") == execution_entity
        ]
        if len(goal_matches) != 1:
            raise ValueError("benchmark destination does not uniquely match binding")
        goal = goal_matches[0]
        if goal.get("frame_id") != "world" or goal.get("unit") != "m":
            raise ValueError("benchmark destination frame or unit is invalid")
        pose = rigid_transform(goal.get("world_T_object_target"))
        target = deepcopy(observed_object)
        target.update(
            entity_ref=target_entity,
            world_T_object_target=pose.reshape(-1).tolist(),
            world_T_functional_target=(
                pose @ np.linalg.inv(rigid_transform(observed_object["world_T_object"]))
                @ rigid_transform(observed_object["world_T_functional_point"])
            ).reshape(-1).tolist(),
        )
        return {
            **{key: request[key] for key in IDENTITY_KEYS},
            "binding_ref": binding_ref,
            "requested_pose": {
                "destination_ref": destination_ref,
                "execution_entity_ref": execution_entity,
                "frame_id": "world",
                "unit": "m",
            },
            "object": target,
            "motion_authorized": False,
        }

    def _observed_support(self, binding):
        """Estimate support and retain residual occupancy without actor meshes."""
        identity = tuple(binding[k] for k in IDENTITY_KEYS)
        understanding = self.understandings[identity]
        refs = {r["object_ref"] for r in understanding.get("relations", [])
                if r.get("predicate") == "on" and r.get("subject_ref") in binding["objects"]}
        if not refs:
            return None  # Consumers requiring support must reject missing evidence.
        if len(refs) != 1:
            raise ValueError("observed support surface is ambiguous")
        ref = next(iter(refs))
        clouds = [a for a in understanding.get("derived_artifacts", [])
                  if a.get("kind") == "object_point_cloud" and a.get("entity_ref") == ref]
        if len(clouds) != 1:
            raise ValueError("observed support requires one metric point cloud")
        cloud = clouds[0]
        if any(cloud.get(k) != binding[k] for k in IDENTITY_KEYS) or cloud.get("frame_id") != binding["frame_id"]:
            raise ValueError("observed support lineage differs from binding")
        points = np.load(_artifact_path(self.root, cloud["artifact_ref"] + ".npy"), allow_pickle=False)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 3 or not np.isfinite(points).all():
            raise ValueError("observed support point cloud is invalid")
        transform = rigid_transform(binding["world_T_observation"])
        world = points @ transform[:3, :3].T + transform[:3, 3]
        try:
            return estimate_support(world, cloud["artifact_ref"], self.support_policy)
        except ValueError as exc:
            raise PreparationProviderError("observed_support_unavailable", str(exc)) from exc


class GroundingEndpoint:
    def __init__(self, resolve):
        self.resolve = resolve

    def invoke(self, arguments):
        try:
            return self.resolve(arguments)
        except (KeyError, ValueError, TypeError, OSError) as exc:
            owner = getattr(self.resolve, "__self__", None)
            diagnostics = getattr(owner, "last_diagnostics", None)
            value = {"status": "unavailable", "motion_authorized": False,
                     "error": {"code": "grounding_unavailable", "message": str(exc)}}
            if isinstance(diagnostics, dict):
                value["diagnostics"] = deepcopy(diagnostics)
            return value


class RememberObservation:
    def __init__(self, endpoint, grounding, tool_id):
        self.endpoint, self.grounding, self.tool_id = endpoint, grounding, tool_id

    def invoke(self, arguments):
        result = self.endpoint.invoke(arguments)
        self.grounding.remember(self.tool_id, result)
        return result
