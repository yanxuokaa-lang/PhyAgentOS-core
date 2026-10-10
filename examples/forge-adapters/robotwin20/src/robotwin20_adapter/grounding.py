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
from .observed_support import SupportEstimationPolicy, estimate_support, estimate_support_from_depth
from .route_evidence import _artifact_path

_DEFERRED_BINDING_AMBIGUITIES = {
    "object_shape_uncertain",
    "metric_3d_unavailable",
    "metric_geometry_unavailable",
    "NO_RELIABLE_METRIC_EXTENTS",
}


def _evidence_error(code, message):
    return PreparationProviderError(
        code,
        message,
        failure_owner="evidence",
        retryable_in_revision=False,
        requires_replan=True,
        recommended_action="refresh_declared_evidence",
        fresh_evidence_requirements=("current_observation_lineage",),
    )


class Grounding:
    def __init__(self, client, root, scene_source, *, support_policy=None, collision_policy=None,
                 goal_source="observation_owned", depth_scale_to_m=0.001):
        self.client, self.root, self.source = client, root, scene_source
        self.support_policy = support_policy or SupportEstimationPolicy()
        self.collision_policy = collision_policy
        self.goal_source = goal_source
        if (isinstance(depth_scale_to_m, bool) or not isinstance(depth_scale_to_m, (int, float))
                or not np.isfinite(depth_scale_to_m) or depth_scale_to_m <= 0):
            raise ValueError("support depth scale must be finite and positive")
        self.depth_scale_to_m = float(depth_scale_to_m)
        self.observations = {}
        self.understandings = {}
        self.bindings = {}
        self.targets = {}
        self.last_diagnostics = None

    def _reject(self, message, *, stage, **details):
        self.last_diagnostics = {"stage": stage, "message": message, **details}
        raise ValueError(message)

    def _require_observation_owned_goal(self):
        if self.goal_source != "observation_owned":
            self._reject(
                "benchmark profile requires a task.goal destination",
                stage="goal_policy",
                code="benchmark_goal_only",
                goal_source=self.goal_source,
            )

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
            "scene_validity": "action_driven",
        }
        actual = {key: state.get(key) for key in expected}
        holding_state = state.get("holding_state")
        if actual["scene_revision"] != expected["scene_revision"]:
            self._reject(
                "scene binding lineage is stale for the current action-driven scene",
                stage="current_scene",
                code="scene_revision_mismatch",
                failure_stage="current_scene",
                retryable=True,
                retryable_in_revision=False,
                requires_replan=True,
                recommended_action="refresh_declared_evidence",
                fresh_evidence_requirements=("current_observation_lineage",),
                expected_scene_revision=expected["scene_revision"],
                actual_scene_revision=actual["scene_revision"],
                expected={**expected, "holding_state": ["empty", "holding"]},
                actual={**actual, "holding_state": holding_state},
            )
        if actual != expected or holding_state not in {"empty", "holding"}:
            self._reject(
                "grounding requires the current stable action-driven scene",
                stage="current_scene",
                expected={**expected, "holding_state": ["empty", "holding"]},
                actual={**actual, "holding_state": holding_state},
            )
        return state

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
        # AgentLoop retries may assemble the same bind node more than once.
        # Reuse the existing current binding for an identical identity and
        # entity set; distinct selections still receive distinct bindings.
        for reference, binding in self.bindings.items():
            if (
                all(binding.get(key) == request[key] for key in IDENTITY_KEYS)
                and set(binding.get("objects", {})) == set(selected)
            ):
                state = self._current(request)
                carried = {
                    item["entity"]["entity_ref"]: item
                    for item in understanding.get("carried_forward", [])
                    if item.get("carry_state") == "held" and item["entity"]["entity_ref"] in selected
                }
                self._carried_objects(carried, binding["scene_facts"], state)
                return {
                    "status": "available",
                    "binding_ref": reference,
                    "motion_authorized": False,
                    **{key: request[key] for key in IDENTITY_KEYS},
                    "frame_id": "world",
                    "unit": "m",
                    "observation_frame_id": binding["frame_id"],
                    "world_T_observation": binding["world_T_observation"],
                    "captured_at": binding["captured_at"],
                    "validity": "current_action_driven_scene",
                    "entities": [
                        {
                            "entity_ref": ref,
                            "execution_entity_ref": item["entity_ref"],
                            "world_T_object": item["world_T_object"],
                            "half_extents_m": item["half_extents_m"],
                        }
                        for ref, item in binding["objects"].items()
                    ],
                    "evidence_refs": [reference],
                }
        selected_set = set(selected)
        carried_by_ref = {
            item.get("entity", {}).get("entity_ref"): item
            for item in understanding.get("carried_forward", [])
            if isinstance(item, Mapping) and isinstance(item.get("entity"), Mapping)
        }
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
            if entity_ref in carried_by_ref:
                continue
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
        current_state = self._current(request)
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
        observed_selected = [ref for ref in selected if ref not in carried_by_ref]
        try:
            objects = correspond(observed_selected, understanding, facts["objects"], camera_to_world)
        except (KeyError, TypeError, ValueError) as exc:
            self._reject(
                "execution correspondence is unavailable or ambiguous",
                stage="execution_correspondence",
                selected_entities=selected,
                error_type=type(exc).__name__,
                reason=str(exc),
            )
        objects = self._project_visual_geometry(
            observed_selected, objects, understanding, camera_to_world
        )
        selected_carried = {
            entity_ref: carried_by_ref[entity_ref]
            for entity_ref in selected
            if entity_ref in carried_by_ref
        }
        objects.update(self._carried_objects(selected_carried, facts, current_state))
        facts = deepcopy(facts)
        # Keep captured execution poses intact for Runtime drift checks. Visual
        # route geometry lives in objects, in its own observation-derived frame.
        current_state = self._current(request)
        self._carried_objects(
            {ref: item for ref, item in selected_carried.items() if item.get("carry_state") == "held"},
            facts, current_state,
        )
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

    def _carried_objects(self, carried_by_ref, current_facts, current_state=None):
        projected = {}
        current_objects = current_facts.get("objects", [])
        for entity_ref, carried in carried_by_ref.items():
            source_binding_ref = carried.get("source_binding_ref")
            execution_ref = carried.get("execution_entity_ref")
            try:
                source_binding = json.loads(
                    _artifact_path(self.root, source_binding_ref).read_text(encoding="utf-8")
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self._reject(
                    "carried entity source binding is unavailable",
                    stage="carry_forward",
                    entity_ref=entity_ref,
                    error_type=type(exc).__name__,
                )
            if (
                source_binding.get("scene_revision") != carried.get("source_scene_revision")
                or source_binding.get("motion_authorized") is not False
            ):
                self._reject(
                    "carried entity source binding identity is invalid",
                    stage="carry_forward",
                    entity_ref=entity_ref,
                )
            source_model = source_binding.get("objects", {}).get(entity_ref)
            source_runtime = [
                item for item in source_binding.get("scene_facts", {}).get("objects", [])
                if isinstance(item, Mapping) and item.get("entity_ref") == execution_ref
            ]
            current_runtime = [
                item for item in current_objects
                if isinstance(item, Mapping) and item.get("entity_ref") == execution_ref
            ]
            if (
                not isinstance(source_model, Mapping)
                or source_model.get("entity_ref") != execution_ref
                or len(source_runtime) != 1
                or len(current_runtime) != 1
            ):
                self._reject(
                    "carried entity execution identity is unavailable",
                    stage="carry_forward",
                    entity_ref=entity_ref,
                )
            try:
                source_pose = rigid_transform(source_runtime[0]["world_T_object"])
                current_pose = rigid_transform(current_runtime[0]["world_T_object"])
            except (KeyError, TypeError, ValueError) as exc:
                self._reject(
                    "carried entity execution pose is invalid",
                    stage="carry_forward",
                    entity_ref=entity_ref,
                    error_type=type(exc).__name__,
                )
            carry_state = carried.get("carry_state", "unchanged")
            if carry_state == "held":
                possession = carried.get("possession")
                if (not isinstance(possession, Mapping) or not isinstance(current_state, Mapping)
                        or possession.get("entity_ref") != entity_ref
                        or possession.get("holding_state") != "holding"
                        or not possession.get("owner") or not possession.get("acquire_invocation_id")
                        or any(current_state.get(key) != possession.get(key)
                               for key in ("holding_state", "owner", "entity_ref", "acquire_invocation_id"))):
                    self._reject("held entity possession no longer matches Runtime", stage="held_projection", entity_ref=entity_ref)
                # Transport the existing observation-derived model with the
                # physical object's rigid displacement. Never substitute actor
                # dimensions or pretend this is a fresh visual measurement.
                delta = current_pose @ np.linalg.inv(source_pose)
                model = deepcopy(dict(source_model))
                for key in ("world_T_object", "world_T_functional_point"):
                    model[key] = (delta @ rigid_transform(model[key])).reshape(-1).tolist()
                projected[entity_ref] = model
                continue
            if carry_state != "unchanged":
                self._reject("carried entity state is invalid", stage="carry_forward", entity_ref=entity_ref)
            if not np.allclose(source_pose, current_pose, atol=1e-6, rtol=0):
                self._reject(
                    "carried entity moved despite unchanged effect evidence",
                    stage="carry_forward",
                    entity_ref=entity_ref,
                )
            projected[entity_ref] = deepcopy(dict(source_model))
        return projected

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

    def staging(self, request):
        self._require_observation_owned_goal()
        if not isinstance(request, Mapping):
            self._reject("staging request must be an object", stage="input_validation")
        binding_ref = request.get("binding_ref")
        entity_ref = request.get("entity_ref")
        if not isinstance(binding_ref, str) or binding_ref not in self.bindings:
            self._reject("staging binding is unavailable", stage="input_validation")
        binding = self.bindings[binding_ref]
        if not isinstance(entity_ref, str) or entity_ref not in binding["objects"]:
            self._reject("staging entity is not in the binding", stage="input_validation")
        self._current(binding)
        try:
            support = self._observed_support(binding)
        except PreparationProviderError:
            raise
        except ValueError as exc:
            raise _evidence_error("observed_support_unavailable", str(exc)) from exc
        center = np.asarray(support.get("position_m"), dtype=float)
        support_half = np.asarray(support.get("half_extents_m"), dtype=float)
        moving = deepcopy(binding["objects"][entity_ref])
        moving_half = np.asarray(moving.get("half_extents_m"), dtype=float)
        if (center.shape != (3,) or support_half.shape != (3,) or moving_half.shape != (3,)
                or not np.isfinite([center, support_half, moving_half]).all()
                or np.any(support_half <= 0) or np.any(moving_half <= 0)):
            self._reject("staging geometry is invalid", stage="staging_geometry")
        clearance = max(0.015, float(self.support_policy.uncertainty_m) * 4.0)
        low = center[:2] - support_half[:2] + moving_half[:2] + clearance
        high = center[:2] + support_half[:2] - moving_half[:2] - clearance
        if np.any(high <= low):
            self._reject("observed support has no staging footprint", stage="staging_search")
        obstacles = []
        for ref, item in binding["objects"].items():
            pose = rigid_transform(item["world_T_object"])
            half = np.asarray(item["half_extents_m"], dtype=float)
            obstacles.append((pose[:2, 3], half[:2], ref))
        for index, item in enumerate(support.get("residual_boxes", [])):
            position = np.asarray(item.get("position_m"), dtype=float)
            half = np.asarray(item.get("half_extents_m"), dtype=float)
            if position.shape == (3,) and half.shape == (3,) and np.isfinite([position, half]).all():
                obstacles.append((position[:2], half[:2], f"residual:{index}"))
        span = np.maximum(high - low, 1e-6)
        footprint = max(float(np.max(moving_half[:2])) * 2.0 + clearance, 0.03)
        counts = np.clip(np.ceil(span / footprint).astype(int) + 1, 3, 11)
        candidates = []
        for x in np.linspace(low[0], high[0], int(counts[0])):
            for y in np.linspace(low[1], high[1], int(counts[1])):
                point = np.asarray([x, y])
                margins = [float(np.max(np.abs(point - position) - (moving_half[:2] + half)))
                           for position, half, _ in obstacles]
                if margins and min(margins) < clearance:
                    continue
                score = min(margins) if margins else float(np.min(span))
                candidates.append((score, float(x), float(y)))
        if not candidates:
            self._reject("no observation-owned staging destination is clear",
                         stage="staging_search", obstacle_count=len(obstacles))
        score, x, y = max(candidates, key=lambda item: (item[0], -abs(item[1] - center[0]),
                                                        -abs(item[2] - center[1]), -item[1], -item[2]))
        pose = rigid_transform(moving["world_T_object"])
        pose[:3, 3] = [x, y, center[2] + support_half[2] + moving_half[2]]
        moving.update(
            entity_ref=entity_ref,
            world_T_object_target=pose.reshape(-1).tolist(),
            world_T_functional_target=(
                pose @ np.linalg.inv(rigid_transform(moving["world_T_object"]))
                @ rigid_transform(moving["world_T_functional_point"])
            ).reshape(-1).tolist(),
        )
        value = {
            **{key: binding[key] for key in IDENTITY_KEYS},
            "binding_ref": binding_ref,
            "requested_pose": {"method": "observed_free_support", "entity_ref": entity_ref},
            "object": moving,
            "support": deepcopy(support),
            "clearance_m": score,
            "motion_authorized": False,
        }
        evidence_ref = self._write("staging-targets", value)
        destination_ref = evidence_ref.replace("artifact://", "destination://", 1)
        self.targets[destination_ref] = value
        return {
            "status": "available", "motion_authorized": False,
            "binding_ref": binding_ref, "entity_ref": entity_ref,
            **{key: binding[key] for key in IDENTITY_KEYS},
            "frame_id": "world", "unit": "m",
            "destination_ref": destination_ref,
            "world_T_object_target": moving["world_T_object_target"],
            "support_evidence_ref": support["evidence_ref"],
            "clearance_m": score,
            "evidence_refs": [binding_ref, support["evidence_ref"], evidence_ref],
        }

    def target(self, request):
        self._require_observation_owned_goal()
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
        if self.goal_source == "benchmark_task_definition":
            value = self._benchmark_goal_target(request, deadline=deadline)
        else:
            value = self.targets.get(request["destination_ref"])
            if value is None:
                raise ValueError("destination is not an observation-owned target")
        request_binding_ref = request.get("binding_ref")
        if request_binding_ref is not None and value["binding_ref"] != request_binding_ref:
            raise ValueError("target scene binding differs from preparation")
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
            raise _evidence_error(
                "observed_collision_coverage_incomplete",
                "observed collision coverage is incomplete; bind all observed obstacles",
            )
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
            depth = self._depth_artifact_for_binding(
                observed, binding, code="observed_collision_unavailable"
            )
            if len(masks) != 1:
                raise _evidence_error(
                    "observed_collision_unavailable",
                    "one target mask in the bound observation view is required",
                )
            mask = masks[0]
            if any(mask.get(k) != binding[k] for k in IDENTITY_KEYS) or mask.get("frame_id") != binding["frame_id"]:
                raise _evidence_error(
                    "observed_collision_unavailable", "target mask lineage differs from binding"
                )
            facts["observed_collision"] = {
                **{k: binding[k] for k in IDENTITY_KEYS}, "frame_id": binding["frame_id"],
                "world_T_camera": binding["world_T_observation"], "depth_ref": depth["ref"],
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
        if self.goal_source == "benchmark_task_definition":
            value = self._benchmark_goal_target(request, deadline=deadline)
        else:
            value = self.targets.get(request["destination_ref"])
            if value is None:
                raise ValueError("destination is not an observation-owned target")
        request_binding_ref = request.get("binding_ref")
        if request_binding_ref is not None and value["binding_ref"] != request_binding_ref:
            raise ValueError("target scene binding differs from preparation")
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
            raise _evidence_error(
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
        binding_ref = request.get("binding_ref")
        if (
            not isinstance(target_entity, str)
            or not isinstance(destination_ref, str)
            or not isinstance(binding_ref, str)
        ):
            raise ValueError("benchmark target request is incomplete")
        binding = self.bindings.get(binding_ref)
        if binding is None:
            raise ValueError("benchmark target scene binding is unavailable")
        if (
            any(binding.get(key) != request.get(key) for key in IDENTITY_KEYS)
            or target_entity not in binding.get("objects", {})
        ):
            raise ValueError("benchmark target scene binding differs from preparation")
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
        refs = sorted({r["object_ref"] for r in understanding.get("relations", [])
                       if r.get("predicate") in {"on", "is_on"}
                       and r.get("subject_ref") in binding["objects"]})
        if not refs:
            return self._observed_support_from_depth(binding, understanding)
        clouds = []
        for ref in refs:
            candidates = [a for a in understanding.get("derived_artifacts", [])
                          if a.get("kind") == "object_point_cloud" and a.get("entity_ref") == ref]
            if len(candidates) != 1:
                raise _evidence_error(
                    "observed_support_unavailable",
                    "observed support requires one metric point cloud per semantic support",
                )
            cloud = candidates[0]
            if (
                any(cloud.get(k) != binding[k] for k in IDENTITY_KEYS)
                or cloud.get("frame_id") != binding["frame_id"]
                or not isinstance(cloud.get("artifact_ref"), str)
            ):
                raise _evidence_error(
                    "observed_support_unavailable",
                    "observed support lineage differs from binding",
                )
            try:
                points = np.load(
                    _artifact_path(self.root, cloud["artifact_ref"] + ".npy"),
                    allow_pickle=False,
                )
            except (EOFError, OSError, ValueError) as exc:
                raise _evidence_error(
                    "observed_support_unavailable",
                    "observed support metric point cloud is unavailable",
                ) from exc
            numeric_points = (
                np.issubdtype(points.dtype, np.integer)
                or np.issubdtype(points.dtype, np.floating)
            )
            if (
                points.ndim != 2
                or points.shape[1] != 3
                or len(points) < 3
                or not numeric_points
                or not np.isfinite(points).all()
            ):
                raise _evidence_error(
                    "observed_support_unavailable",
                    "observed support point cloud is invalid",
                )
            clouds.append((cloud["artifact_ref"], points))
        canonical_ref, canonical_points = clouds[0]
        if any(not np.array_equal(points, canonical_points) for _, points in clouds[1:]):
            raise _evidence_error(
                "observed_support_unavailable",
                "observed support surface is ambiguous across distinct metric geometries",
            )
        transform = rigid_transform(binding["world_T_observation"])
        world = canonical_points @ transform[:3, :3].T + transform[:3, 3]
        try:
            support = estimate_support(world, canonical_ref, self.support_policy)
        except ValueError as exc:
            raise _evidence_error("observed_support_unavailable", str(exc)) from exc
        if len(clouds) > 1:
            support["source_refs"] = [ref for ref, _ in clouds]
        return support

    def _observed_support_from_depth(self, binding, understanding):
        identity = tuple(binding[k] for k in IDENTITY_KEYS)
        observed = self.observations[identity]
        depth_artifact = self._depth_artifact_for_binding(
            observed, binding, code="observed_support_unavailable"
        )

        entities = understanding.get("entities", [])
        masks = [item for item in understanding.get("derived_artifacts", [])
                 if item.get("kind") == "instance_mask"]
        entity_refs = [item.get("entity_ref") for item in entities if isinstance(item, Mapping)]
        if (len(entity_refs) != len(entities)
                or any(not isinstance(ref, str) or not ref for ref in entity_refs)
                or len(set(entity_refs)) != len(entity_refs)):
            raise _evidence_error(
                "observed_support_unavailable", "current scene entities have invalid identities"
            )
        mask_refs = [item.get("entity_ref") for item in masks]
        if (not entity_refs or len(masks) != len(entity_refs)
                or any(not isinstance(ref, str) or not ref for ref in mask_refs)
                or set(mask_refs) != set(entity_refs)):
            raise _evidence_error(
                "observed_support_unavailable", "one current instance mask per observed entity is required"
            )
        for mask in masks:
            if (any(mask.get(key) != binding[key] for key in IDENTITY_KEYS)
                    or mask.get("frame_id") != binding["frame_id"]):
                raise _evidence_error(
                    "observed_support_unavailable", "instance mask lineage differs from binding"
                )

        try:
            calibration = json.loads(
                _artifact_path(self.root, binding["calibration_ref"]).read_text(encoding="utf-8")
            )
            intrinsic = calibration["intrinsic_cv"]
            depth = np.load(_artifact_path(self.root, depth_artifact["ref"] + ".npy"), allow_pickle=False)
            excluded_masks = [
                np.load(_artifact_path(self.root, item["artifact_ref"] + ".npy"), allow_pickle=False)
                for item in masks
            ]
            return estimate_support_from_depth(
                depth,
                intrinsic,
                binding["world_T_observation"],
                excluded_masks,
                depth_artifact["ref"],
                excluded_mask_refs=[item["artifact_ref"] for item in masks],
                depth_scale_to_m=self.depth_scale_to_m,
                policy=self.support_policy,
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise _evidence_error("observed_support_unavailable", str(exc)) from exc

    @staticmethod
    def _depth_artifact_for_binding(observed, binding, *, code):
        """Resolve one depth artifact from the observation view bound to planning."""

        observed_frame = observed.get("frame")
        if (
            any(observed.get(key) != binding[key] for key in IDENTITY_KEYS)
            or not isinstance(observed_frame, Mapping)
            or observed_frame.get("frame_id") != binding["frame_id"]
        ):
            raise _evidence_error(code, "scene observation lineage differs from binding")

        views = observed.get("views")
        if isinstance(views, list) and views:
            matching_views = [
                view
                for view in views
                if isinstance(view, Mapping)
                and view.get("observation_ref") == binding["observation_ref"]
                and view.get("calibration_ref") == binding["calibration_ref"]
                and isinstance(view.get("frame"), Mapping)
                and view["frame"].get("frame_id") == binding["frame_id"]
            ]
            if len(matching_views) != 1:
                raise _evidence_error(
                    code, "bound observation view is absent or ambiguous"
                )
            depths = [
                item
                for item in matching_views[0].get("artifacts", [])
                if isinstance(item, Mapping) and item.get("kind") == "depth"
            ]
        else:
            depths = [
                item
                for item in observed.get("artifacts", [])
                if isinstance(item, Mapping) and item.get("kind") == "depth"
            ]
        if len(depths) != 1 or not isinstance(depths[0].get("ref"), str):
            raise _evidence_error(
                code, "one depth artifact from the bound observation view is required"
            )
        depth = depths[0]
        artifact_lineage = {
            "observation_ref": binding["observation_ref"],
            "scene_revision": binding["scene_revision"],
            "calibration_ref": binding["calibration_ref"],
            "frame_id": binding["frame_id"],
        }
        if any(
            key in depth and depth.get(key) != value
            for key, value in artifact_lineage.items()
        ):
            raise _evidence_error(code, "depth artifact lineage differs from binding")
        return depth


class GroundingEndpoint:
    def __init__(self, resolve):
        self.resolve = resolve

    def invoke(self, arguments):
        try:
            return self.resolve(arguments)
        except (KeyError, ValueError, TypeError, OSError) as exc:
            owner = getattr(self.resolve, "__self__", None)
            diagnostics = getattr(owner, "last_diagnostics", None)
            code = (
                diagnostics.get("code", "grounding_unavailable")
                if isinstance(diagnostics, dict)
                else "grounding_unavailable"
            )
            error = {"code": code, "message": str(exc)}
            if isinstance(diagnostics, dict):
                for key in (
                    "failure_stage",
                    "retryable",
                    "retryable_in_revision",
                    "requires_replan",
                    "recommended_action",
                    "fresh_evidence_requirements",
                    "expected_scene_revision",
                    "actual_scene_revision",
                ):
                    if key in diagnostics:
                        error[key] = deepcopy(diagnostics[key])
            value = {"status": "unavailable", "motion_authorized": False,
                     "error": error}
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
