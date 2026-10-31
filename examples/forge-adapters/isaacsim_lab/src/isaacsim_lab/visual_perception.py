"""Visual labels, model segmentation and observed depth behind standard Query ports."""

from __future__ import annotations

import base64
import io
import json
from collections import Counter
from copy import deepcopy
from uuid import uuid4

import numpy as np
from scipy.spatial.transform import Rotation

from .visual_geometry import (
    candidate_world_pose,
    pixel_to_world,
    process_features,
    world_from_camera,
)


class RGBLabelPointInference:
    """Deployment-owned model client; no scene IDs or task success enter its input."""

    def __init__(self, client, *, model, max_output_tokens=4096):
        self.client, self.model, self.max_output_tokens = client, model, max_output_tokens

    def infer(self, image):
        from PIL import Image

        width, height = Image.open(io.BytesIO(image.data)).size
        schema = {"type": "object", "additionalProperties": False, "required": ["objects", "ambiguities"],
                  "properties": {"objects": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False,
                      "required": ["category", "label", "pixel_xy", "bbox_xyxy", "confidence", "identity_resolved", "process_evidence"],
                      "properties": {
                          "category": {"enum": ["reagent_bottle", "mixing_vessel", "stir_tool", "test_tube"]},
                          "label": {"type": ["string", "null"]},
                          "bbox_xyxy": {"type": "array", "minItems": 4, "maxItems": 4, "items": {"type": "integer"}},
                          "pixel_xy": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "number"}},
                          "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                          "identity_resolved": {"type": "boolean"},
                          "process_evidence": {"type": "object", "additionalProperties": False,
                              "required": ["kind", "pixels_xy", "fully_visible"], "properties": {
                                  "kind": {"enum": ["unavailable", "rim", "rod_endpoints"]},
                                  "pixels_xy": {"type": "array", "items": {"type": "array", "minItems": 2,
                                      "maxItems": 2, "items": {"type": "number"}}},
                                  "fully_visible": {"type": "boolean"}}}}}},
                      "ambiguities": {"type": "array", "items": {"type": "string"}}}}
        response = self.client.responses.create(
            model=self.model, store=False, max_output_tokens=self.max_output_tokens,
            instructions=("Inspect the laboratory RGB image. Enumerate visible reagent bottles, beakers, test tubes and stirring tools. Do not classify test tubes as mixing vessels. "
                          "Read attached labels literally, including short alphanumeric identifiers at the edges or corners "
                          "and every legible line; preserve line breaks. Inspect the entire attached label before returning "
                          "its transcription. Never fill missing characters from expected names or surrounding objects; "
                          "report partially unreadable text in ambiguities and use null when unreadable. "
                          "For each object give one pixel on its visible "
                          "physical surface, away from its label, background, rim, gripper, stand and occluders. Also give a tight bbox_xyxy of the physical object excluding its label/support. Coordinates use "
                          "the original image resolution, x right and y down. For a thin rod select the midpoint of a clearly "
                          "visible shaft segment. Do not infer chemical contents or emit simulator IDs, metric geometry, "
                          "motion commands or success. Set identity_resolved=false if the object, its label association "
                          "or its surface pixel is uncertain. Report that uncertainty in ambiguities. "
                          "Keep recognizable objects even when their label is unreadable; report identity uncertainty separately. "
                          "For process_evidence give pixels only for visually identifiable physical landmarks: eight or more "
                          "points around a fully visible open rim, or both physical rod endpoints ordered non-working then working. "
                          "Set unavailable/empty/false if hidden, ambiguous or the working end is unknown. "
                          "Never use label edges, silhouette maxima or occlusion boundaries as these landmarks. "
                          "An occluded object does not invalidate other clearly identified objects."),
            input=[{"role": "user", "content": [{"type": "input_text", "text": f"Original image: {width} by {height} pixels."},
                    {"type": "input_image", "detail": "high",
                     "image_url": f"data:{image.media_type};base64,{base64.b64encode(image.data).decode()}"}]}],
            text={"format": {"type": "json_schema", "name": "laboratory_visual_points", "strict": True, "schema": schema}},
        )
        output_text = response.output_text or ""
        try:
            result = json.loads(output_text)
        except json.JSONDecodeError as exc:
            start = max(0, exc.pos - 240)
            exc.response_diagnostics = {
                "output_length": len(output_text),
                "line": exc.lineno,
                "column": exc.colno,
                "position": exc.pos,
                "excerpt": output_text[start:start + 640],
            }
            raise
        return result


class LabArtifactStore:
    """Resolve the Isaac capture namespace for existing model Provider ports."""

    def __init__(self, root):
        from pathlib import Path
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, ref):
        prefix = "artifact://labutopia/"
        if not isinstance(ref, str) or not ref.startswith(prefix):
            raise ValueError("artifact is outside the configured namespace")
        path = (self.root / ref[len(prefix):]).resolve()
        if self.root not in path.parents:
            raise ValueError("artifact escapes the configured root")
        return path

    def resolve_point_cloud(self, ref):
        path = self.path(ref)
        if not path.is_file():
            raise ValueError("point-cloud artifact is unavailable")
        return path

    def write(self, kind, value):
        from uuid import uuid4

        from PhyAgentOS.utils.atomic_file import atomic_write_bytes
        array = isinstance(value, np.ndarray)
        ref = f"artifact://labutopia/{kind}/{uuid4().hex}.{'npy' if array else 'json'}"
        if array:
            buffer = io.BytesIO()
            np.save(buffer, value, allow_pickle=False)
            data = buffer.getvalue()
        else:
            data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        atomic_write_bytes(self.path(ref), data)
        return ref


def _grasp_candidate_index_key(candidate_set_ref, calibration_ref):
    return candidate_set_ref, calibration_ref


class RecordedGraspProvider:
    """Persist actual model inputs/output and capture-specific candidate refs."""

    def __init__(self, provider, store):
        self.provider, self.store = provider, store
        self.captures = {}
        self.candidate_sets = {}

    def propose(self, request):
        output = deepcopy(dict(self.provider.propose(request)))
        evidence = self.store.write("grasp-predictions", {"request": request, "result": output})
        capture = evidence.rsplit("/", 1)[1].removesuffix(".json")
        candidates = []
        for item in output["candidates"]:
            candidate = dict(item)
            candidate["candidate_ref"] = f"candidate://{item['entity_ref'].removeprefix('entity://')}/{capture}-{len(candidates)}"
            candidate["provenance"] = [*candidate["provenance"], evidence]
            candidates.append(candidate)
        output["candidates"] = candidates
        output["produced_evidence_refs"] = [*output.get("produced_evidence_refs", []), evidence]
        candidate_set_ref = f"candidate-set://{request['scene_revision']}/{request['frame_id']}"
        index_key = _grasp_candidate_index_key(candidate_set_ref, request["calibration_ref"])
        identity = {key: request[key] for key in
                    ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        candidate_set = self.candidate_sets.get(index_key)
        if candidate_set is not None and any(candidate_set.get(key) != value for key, value in identity.items()):
            raise ValueError("grasp candidate-set identity changed for an existing capture")
        if candidate_set is None:
            candidate_set = {
                "candidate_set_ref": candidate_set_ref,
                **identity,
                "entities": set(),
                "candidate_refs": set(),
            }
            self.candidate_sets[index_key] = candidate_set
        candidate_set["entities"].update(target["entity_ref"] for target in request["targets"])
        candidate_set["candidate_refs"].update(item["candidate_ref"] for item in candidates)
        self.captures.setdefault(request["calibration_ref"], {}).update(
            {item["candidate_ref"]: deepcopy(item) for item in candidates})
        return output

    def candidate(self, binding):
        item = self.captures.get(binding["calibration_ref"], {}).get(binding["candidate_ref"])
        if item is None or dict(item) != dict(binding["grasp_candidate"]):
            raise ValueError("selected grasp differs from the model prediction for this capture")
        return item

    def close(self):
        self.provider.release()


class LabGraspTaskAffordanceProvider:
    """Qualify same-capture grasp/process combinations without selecting one."""

    def __init__(self, perception: "LabVisualPerception", *, support_tolerance_m=0.012,
                 bottle_opening_clearance_ratio=0.08, bottle_max_axial_approach_dot=0.7,
                 rod_endpoint_ambiguity_ratio=0.12, rod_grasp_end_margin_ratio=0.15):
        values = (support_tolerance_m, bottle_opening_clearance_ratio,
                  bottle_max_axial_approach_dot, rod_endpoint_ambiguity_ratio,
                  rod_grasp_end_margin_ratio)
        if any(isinstance(value, bool) or not np.isfinite(float(value)) for value in values):
            raise ValueError("task-affordance thresholds must be finite numbers")
        if support_tolerance_m <= 0 or not 0 < bottle_opening_clearance_ratio < 1:
            raise ValueError("task-affordance support and opening-clearance thresholds are invalid")
        if not 0 < bottle_max_axial_approach_dot < 1:
            raise ValueError("bottle approach threshold must be between zero and one")
        if not 0 < rod_endpoint_ambiguity_ratio < 0.5 or not 0 < rod_grasp_end_margin_ratio < 0.5:
            raise ValueError("rod endpoint thresholds must be between zero and one half")
        self.perception = perception
        self.support_tolerance_m = float(support_tolerance_m)
        self.bottle_opening_clearance_ratio = float(bottle_opening_clearance_ratio)
        self.bottle_max_axial_approach_dot = float(bottle_max_axial_approach_dot)
        self.rod_endpoint_ambiguity_ratio = float(rod_endpoint_ambiguity_ratio)
        self.rod_grasp_end_margin_ratio = float(rod_grasp_end_margin_ratio)
        self.candidate_sets = {}

    def propose(self, request):
        identity = {key: request[key] for key in
                    ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        records = self.perception._records(request)
        grasp_set = self.perception.grasps.candidate_sets.get(_grasp_candidate_index_key(
            request["grasp_candidate_set_ref"], request["calibration_ref"]))
        feature_set = self.perception.process_feature_sets.get(request["process_feature_candidate_set_ref"])
        expected = set(request["entity_refs"])
        grasp_entity = request["entity_refs"][0]
        if (grasp_set is None or feature_set is None
                or any(grasp_set.get(key) != identity[key] or feature_set.get(key) != identity[key]
                       for key in identity)
                or not expected <= set(records)
                or grasp_entity not in grasp_set["entities"]
                or set(feature_set["entity_refs"]) != expected
                or feature_set.get("candidate_set_ref") != request["process_feature_candidate_set_ref"]
                or grasp_set.get("candidate_set_ref") != request["grasp_candidate_set_ref"]):
            return {"status": "stale", "candidate_set_ref": "grasp-affordance-set://unavailable",
                    "grasp_candidate_set_ref": request["grasp_candidate_set_ref"],
                    "process_feature_candidate_set_ref": request["process_feature_candidate_set_ref"],
                    **identity, "candidates": [], "error": "grasp/process evidence is not from the same capture"}

        source_ref, destination_ref = request["entity_refs"]
        selected_features = []
        for feature_ref in request["selected_process_feature_refs"]:
            item = feature_set["candidates"].get(feature_ref)
            if item is None:
                return {"status": "stale", "candidate_set_ref": "grasp-affordance-set://unavailable",
                        "grasp_candidate_set_ref": request["grasp_candidate_set_ref"],
                        "process_feature_candidate_set_ref": request["process_feature_candidate_set_ref"],
                        **identity, "candidates": [], "error": "selected process feature is not in the current capture"}
            selected_features.append((feature_ref, item[0], item[2]))
        source = records[source_ref]
        source_features = [(ref, feature) for ref, entity, feature in selected_features if entity == source_ref]
        destination_features = [(ref, feature) for ref, entity, feature in selected_features if entity == destination_ref]
        grasp_candidates = self._grasp_candidates(grasp_set, request, source_ref)
        qualified, failures = [], []
        if request["operation"] == "pour":
            if (len(source_features) != 1 or len(destination_features) != 1
                    or source_features[0][1].get("feature_kind") != "rim"
                    or destination_features[0][1].get("feature_kind") != "rim"):
                failures.append("pour requires one source rim and one destination rim")
            elif (source_features[0][1].get("feature_role") != "pour_lip"
                  or not self._valid_pour_direction(source_features[0][1])):
                failures.append("source geometry does not identify a pour lip and outward flow direction")
            else:
                process_refs = [source_features[0][0], destination_features[0][0]]
                for candidate_ref, candidate in grasp_candidates:
                    accepted, reason = self._qualify_bottle_grasp(candidate, source, source_features[0][1])
                    if accepted:
                        qualified.append({"entity_ref": source_ref, "grasp_candidate_ref": candidate_ref,
                                          "process_feature_refs": process_refs})
                    elif reason:
                        failures.append(reason)
        else:
            rod_ends = [(ref, feature) for ref, feature in source_features
                        if feature.get("feature_kind") == "rod_endpoint_pair"]
            rims = [(ref, feature) for ref, feature in destination_features
                    if feature.get("feature_kind") == "rim"]
            if len(rod_ends) != 2 or len(rims) != 1 or len(source_features) != 2 or len(destination_features) != 1:
                failures.append("stir requires both rod endpoints and one destination rim")
            else:
                for candidate_ref, candidate in grasp_candidates:
                    working_ref, reason = self._working_endpoint(candidate, source, rod_ends)
                    if working_ref:
                        qualified.append({"entity_ref": source_ref, "grasp_candidate_ref": candidate_ref,
                                          "process_feature_refs": [working_ref, rims[0][0]]})
                    elif reason:
                        failures.append(reason)

        candidate_set_ref = f"grasp-affordance-set://{uuid4().hex}"
        combinations = {}
        candidates = []
        for item in qualified:
            combination_ref = f"grasp-affordance://{uuid4().hex}"
            combination = {"combination_ref": combination_ref, **item}
            combinations[combination_ref] = combination
            candidates.append(combination)
        self.candidate_sets[candidate_set_ref] = {
            **identity, "operation": request["operation"], "entity_refs": expected,
            "grasp_candidate_set_ref": request["grasp_candidate_set_ref"],
            "process_feature_candidate_set_ref": request["process_feature_candidate_set_ref"],
            "combinations": combinations,
        }
        status = "available" if candidates else ("ambiguous" if any("ambiguous" in item for item in failures) else "unavailable")
        return {"status": status, "candidate_set_ref": candidate_set_ref,
                "grasp_candidate_set_ref": request["grasp_candidate_set_ref"],
                "process_feature_candidate_set_ref": request["process_feature_candidate_set_ref"],
                **identity, "candidates": candidates,
                **({"error": "; ".join(dict.fromkeys(failures))} if failures and not candidates else {})}

    @staticmethod
    def _valid_pour_direction(feature):
        direction = np.asarray(feature.get("pour_direction_world"), dtype=float)
        axis = np.asarray(feature.get("axis_world"), dtype=float)
        if (direction.shape != (3,) or axis.shape != (3,) or not np.isfinite(direction).all()
                or not np.isfinite(axis).all()):
            return False
        direction_norm, axis_norm = float(np.linalg.norm(direction)), float(np.linalg.norm(axis))
        return direction_norm > 1e-9 and axis_norm > 1e-9 and abs(float(np.dot(direction / direction_norm, axis / axis_norm))) < 0.5

    def validate_selection(self, request):
        identity = {key: request[key] for key in
                    ("candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref",
                     "observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        candidate_set = self.candidate_sets.get(request["candidate_set_ref"])
        if candidate_set is None or any(candidate_set.get(key) != request[key] for key in (
            "process_feature_candidate_set_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )):
            return {"status": "stale", **identity, "error": "task-affordance candidate set is stale"}
        combination = candidate_set["combinations"].get(request["selected_combination_ref"])
        if combination is None:
            return {"status": "stale", **identity, "error": "selected combination is not in the current Query"}
        grasp_set = self.perception.grasps.candidate_sets.get(_grasp_candidate_index_key(
            candidate_set["grasp_candidate_set_ref"], request["calibration_ref"]))
        feature_set = self.perception.process_feature_sets.get(candidate_set["process_feature_candidate_set_ref"])
        if (grasp_set is None or feature_set is None
                or any(grasp_set.get(key) != candidate_set[key] or feature_set.get(key) != candidate_set[key]
                       for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref"))
                or feature_set.get("candidate_set_ref") != candidate_set["process_feature_candidate_set_ref"]
                or grasp_set.get("candidate_set_ref") != candidate_set["grasp_candidate_set_ref"]):
            return {"status": "stale", **identity, "error": "selected combination evidence is no longer current"}
        if (combination.get("grasp_candidate_ref") not in grasp_set.get("candidate_refs", set())
                or combination.get("grasp_candidate_ref") not in
                self.perception.grasps.captures.get(request["calibration_ref"], {})
                or any(ref not in feature_set.get("candidates", {}) for ref in combination.get("process_feature_refs", ()) )):
            return {"status": "stale", **identity, "error": "selected combination references missing evidence"}
        return {"status": "available", **identity,
                "selected": {key: combination[key] for key in
                             ("combination_ref", "grasp_candidate_ref", "process_feature_refs")}}

    def _grasp_candidates(self, grasp_set, request, source_ref):
        captured = self.perception.grasps.captures.get(request["calibration_ref"], {})
        return [(ref, captured[ref]) for ref in grasp_set["candidate_refs"]
                if ref in captured and captured[ref].get("entity_ref") == source_ref]

    def _candidate_pose(self, candidate, record):
        frame = candidate.get("grasp_frame", {})
        approach = candidate.get("approach_direction", {})
        if frame.get("frame_id") != record["frame_id"] or approach.get("frame_id") != record["frame_id"]:
            return None
        position = np.asarray(frame.get("position_m"), dtype=float)
        direction = np.asarray(approach.get("vector"), dtype=float)
        transform = np.asarray(record["world_from_camera"], dtype=float)
        if (position.shape != (3,) or direction.shape != (3,) or transform.shape != (4, 4)
                or not np.isfinite(position).all() or not np.isfinite(direction).all()
                or not np.isfinite(transform).all()):
            return None
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-9:
            return None
        return transform[:3, :3] @ position + transform[:3, 3], transform[:3, :3] @ (direction / norm)

    def _world_points(self, record):
        try:
            points = np.asarray(np.load(self.perception.store.path(record["points_ref"]), allow_pickle=False), dtype=float)
            transform = np.asarray(record["world_from_camera"], dtype=float)
        except (OSError, TypeError, ValueError, KeyError):
            return None
        if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 3 or not np.isfinite(points).all()
                or transform.shape != (4, 4) or not np.isfinite(transform).all()):
            return None
        return points @ transform[:3, :3].T + transform[:3, 3]

    def _support_limit(self, candidate):
        geometry = candidate.get("grasp_geometry") or {}
        extents = [float(geometry[key]) for key in ("width_m", "height_m", "depth_m")
                   if isinstance(geometry.get(key), (int, float)) and float(geometry[key]) > 0]
        return max([self.support_tolerance_m, *(value * .75 for value in extents)])

    def _qualify_bottle_grasp(self, candidate, record, rim):
        pose, points = self._candidate_pose(candidate, record), self._world_points(record)
        if pose is None or points is None:
            return False, "bottle grasp pose or point-cloud evidence is unavailable"
        tip = np.asarray(rim.get("tip_world"), dtype=float)
        axis = np.asarray(rim.get("axis_world"), dtype=float)
        if tip.shape != (3,) or axis.shape != (3,) or not np.isfinite(tip).all() or not np.isfinite(axis).all():
            return False, "bottle opening geometry is unresolved"
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-9:
            return False, "bottle opening axis is unresolved"
        axis /= axis_norm
        position, approach = pose
        projections = (points - tip) @ axis
        candidate_projection = float(np.dot(position - tip, axis))
        extent = float(np.ptp(projections))
        clearance = max(float(rim.get("rim_radius_m", 0.0)) * 2., extent * self.bottle_opening_clearance_ratio)
        if candidate_projection >= -clearance:
            return False, "bottle grasp is too close to the opening"
        if candidate_projection < float(np.quantile(projections, .02)) - self._support_limit(candidate):
            return False, "bottle grasp is outside the observed body support"
        if float(np.min(np.linalg.norm(points - position, axis=1))) > self._support_limit(candidate):
            return False, "bottle grasp has no nearby observed body support"
        if abs(float(np.dot(approach, axis))) > self.bottle_max_axial_approach_dot:
            return False, "bottle grasp approach may occlude the opening"
        return True, ""

    def _working_endpoint(self, candidate, record, endpoints):
        pose, points = self._candidate_pose(candidate, record), self._world_points(record)
        if pose is None or points is None:
            return None, "rod grasp pose or point-cloud evidence is unavailable"
        ends = [(ref, np.asarray(feature.get("origin_world"), dtype=float)) for ref, feature in endpoints]
        if any(point.shape != (3,) or not np.isfinite(point).all() for _, point in ends):
            return None, "rod endpoint geometry is unresolved"
        first, second = ends[0][1], ends[1][1]
        segment = second - first
        length = float(np.linalg.norm(segment))
        if length <= 1e-9:
            return None, "rod endpoints coincide"
        position = pose[0]
        projection = float(np.dot(position - first, segment) / (length * length))
        closest = first + np.clip(projection, 0., 1.) * segment
        if float(np.linalg.norm(position - closest)) > self._support_limit(candidate):
            return None, "rod grasp has no nearby shaft support"
        margin = self.rod_grasp_end_margin_ratio
        if projection <= margin or projection >= 1. - margin:
            return None, "rod grasp is at an endpoint rather than on the shaft"
        distances = [float(np.linalg.norm(position - point)) for _, point in ends]
        if abs(distances[0] - distances[1]) <= length * self.rod_endpoint_ambiguity_ratio:
            return None, "rod working end is ambiguous relative to the grasp"
        return ends[0 if distances[0] > distances[1] else 1][0], ""


class LabVisualPerception:
    """Compose existing segmentation/localization Providers; no grasp synthesis.

    Observed geometry and private execution correspondence are separate stores.
    Only RGB-D-derived artifacts are published through scene.understand.
    """

    def __init__(self, engine, artifact_resolver, inference, *, segmentation, geometry, store, grasps,
                 provider_from_tcp, truth_manifest=None):
        from robotwin20_adapter.single_view_perception import NumpyMetricLocalizationProvider
        self.engine, self.resolver, self.inference = engine, artifact_resolver, inference
        self.segmentation, self.store, self.grasps = segmentation, store, grasps
        self.geometry = geometry
        self.localization = NumpyMetricLocalizationProvider(depth_scale_to_m=1.)
        self.provider_from_tcp = np.asarray(provider_from_tcp, dtype=float)
        self.truth_manifest = truth_manifest
        if (self.provider_from_tcp.shape != (4, 4) or not np.isfinite(self.provider_from_tcp).all()
                or not np.allclose(self.provider_from_tcp[3], [0, 0, 0, 1])
                or not np.allclose(self.provider_from_tcp[:3, :3].T @ self.provider_from_tcp[:3, :3], np.eye(3))
                or np.linalg.det(self.provider_from_tcp[:3, :3]) < 0):
            raise ValueError("provider_from_tcp must be a rigid calibrated transform")
        self.observations, self.identities, self.capabilities = {}, {}, {}
        self.captures, self.labels = {}, {}
        self.process_feature_sets = {}
        self.diagnostics = {}

    def diagnostic_summary(self):
        return dict(self.diagnostics)

    def understand(self, request):
        self.diagnostics = {}
        key = request["calibration_ref"]
        if key in self.captures:
            previous, result = self.captures[key]
            if any(previous[k] != request[k] for k in
                   ("observation_ref", "scene_revision", "frame_id", "artifacts")):
                raise ValueError("capture identity changed for an existing calibration")
            return deepcopy(result)
        try:
            result = self._understand(request)
            self.captures[key] = (deepcopy(request), deepcopy(result))
            return result
        except Exception as exc:
            failure = {"request": request, "error_type": type(exc).__name__, "error": str(exc)}
            response_diagnostics = getattr(exc, "response_diagnostics", None)
            if response_diagnostics is not None:
                failure["response_diagnostics"] = response_diagnostics
            self.store.write("perception-failure", failure)
            self.diagnostics = {"reason": "provider_failure"}
            raise

    def _understand(self, request):
        if self.truth_manifest is not None:
            return self._understand_simulator_truth(request, self.truth_manifest)
        from PIL import Image
        from robotwin20_adapter.geometry_recovery import GeometryRecoveryRequest
        from robotwin20_adapter.single_view_perception import (
            LocalizationRequest,
            Proposal,
            SegmentationRequest,
        )

        rgb_ref = next(ref for ref in request["artifacts"] if ref.startswith("artifact://labutopia/rgb/"))
        depth_ref = next(ref for ref in request["artifacts"] if ref.startswith("artifact://labutopia/depth/"))
        image = self.resolver.resolve(rgb_ref)
        if image is None:
            raise ValueError("RGB artifact is unavailable")
        calibration = json.loads(self.resolver.resolve(request["calibration_ref"]).data)
        if any(calibration[k] != request[k] for k in ("scene_revision", "frame_id")):
            raise ValueError("calibration does not belong to the capture")
        transform = world_from_camera(calibration)
        depth = np.load(io.BytesIO(self.resolver.resolve(depth_ref).data), allow_pickle=False)
        width, height = Image.open(io.BytesIO(image.data)).size
        if depth.shape != (height, width):
            raise ValueError("capture RGB and depth are not aligned")
        identity = {key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        inferred = self.inference.infer(image)
        inference_ref = self.store.write("visual-inference", {"request": request, "result": inferred})
        claims = inferred["objects"]
        label_counts = Counter((c["category"], c.get("label")) for c in claims if c.get("label"))
        segmented, ambiguities = [], list(inferred.get("ambiguities", []))
        try:
            for index, claim in enumerate(claims):
                bbox = tuple(claim["bbox_xyxy"])
                if (len(bbox) != 4 or not 0 <= bbox[0] < bbox[2] <= width
                        or not 0 <= bbox[1] < bbox[3] <= height):
                    ambiguities.append(f"object {index}: visual proposal bbox is outside the image")
                    continue
                # Worker failure is a provider failure, not an object absence.
                mask = np.asarray(self.segmentation.segment(SegmentationRequest(
                    observation_ref=request["observation_ref"], scene_revision=request["scene_revision"],
                    entity_ref=f"entity://proposal-{index}", frame_id=request["frame_id"], rgb_artifact_ref=rgb_ref,
                    rgb_path=self.store.path(rgb_ref), width_px=width, height_px=height,
                    proposal=Proposal(bbox, claim["confidence"]))).mask, dtype=bool)
                if mask.shape != (height, width):
                    raise ValueError("segmentation output dimensions differ from capture")
                pixel = np.asarray(claim["pixel_xy"], dtype=float)
                if pixel.shape != (2,) or not np.isfinite(pixel).all():
                    ambiguities.append(f"object {index}: visual surface pixel is invalid")
                    continue
                x, y = np.rint(pixel).astype(int)
                if not (0 <= x < width and 0 <= y < height) or not mask[y, x]:
                    ambiguities.append(f"object {index}: visual identity pixel is not inside the model instance mask")
                    continue
                segmented.append((claim, mask, self.store.write("instance-mask", mask)))
        finally:
            self.segmentation.release()
        entities, envelopes, derived, records = [], [], [], {}
        if segmented:
            union = np.logical_or.reduce([item[1] for item in segmented])
            union_ref = self.store.write("transparent-mask", union)
            try:
                recovered = self.geometry.recover(GeometryRecoveryRequest(**identity,
                    rgb_path=self.store.path(rgb_ref), depth_path=self.store.path(depth_ref),
                    mask_path=self.store.path(union_ref), image_size_px=(width, height)))
            finally:
                self.geometry.release()
            restored = np.asarray(recovered.depth_m)
            if restored.shape != depth.shape or recovered.metadata.get("unit") != "m":
                raise ValueError("geometry recovery changed image dimensions or metric units")
            recovery_ref = self.store.write("recovered-depth", restored)
            recovery_metadata_ref = self.store.write("geometry-recovery", {**identity,
                "source_refs": [rgb_ref, depth_ref, union_ref], "depth_ref": recovery_ref,
                "metadata": dict(recovered.metadata)})
        for claim, mask, mask_ref in segmented:
            label = claim.get("label") if claim.get("identity_resolved", True) else None
            if label and label_counts[(claim["category"], label)] > 1:
                ambiguities.append(f"duplicate visible label {label}: identity unresolved")
                label = None
            entity = (self.labels.setdefault((claim["category"], label), f"entity://observed-{uuid4().hex}")
                      if label else f"entity://observed-{uuid4().hex}")
            common = {**identity, "entity_ref": entity}
            entities.append({"entity_ref": entity, "category": claim["category"], "confidence": claim["confidence"],
                             **({"label": label} if label else {}), "provenance": [rgb_ref]})
            def artifact(ref, kind, descriptor, sources, provenance):
                descriptor = {**dict.fromkeys(("width_px", "height_px", "bbox_xyxy_px", "foreground_pixels",
                    "point_count", "unit", "min_xyz_m", "max_xyz_m", "confidence")), **descriptor}
                return {"artifact_ref": ref, "kind": kind, "media_type": "application/numpy", **common,
                        "source_refs": sources, "provenance": provenance, "descriptor": descriptor}
            derived.append(artifact(mask_ref, "instance_mask", {"width_px": width, "height_px": height,
                "bbox_xyxy_px": claim["bbox_xyxy"], "foreground_pixels": int(mask.sum())}, [rgb_ref], [rgb_ref]))
            try:
                valid_surface = mask & np.isfinite(restored) & (restored > 0)
                if valid_surface.sum() < 20:
                    raise ValueError("instance has insufficient valid recovered surface")
                measured = self.localization.localize(LocalizationRequest(valid_surface, restored, {
                    "camera_name": request["frame_id"], "intrinsic_cv": calibration["intrinsics"],
                    "extrinsic_cv": np.linalg.inv(transform).tolist()}, request["frame_id"]))
                points = np.asarray(measured.points_xyz_m)
            except ValueError as exc:
                ambiguities.append(f"{entity}: geometry unavailable: {exc}")
                self.store.write("object-geometry-failure", {**common, "error": str(exc),
                    "source_refs": [mask_ref, recovery_metadata_ref]})
                continue
            world_points = points @ transform[:3, :3].T + transform[:3, 3]
            features = None
            try:
                evidence = claim.get("process_evidence")
                support = None
                if evidence and evidence["kind"] != "unavailable":
                    pixels = np.asarray(evidence["pixels_xy"], dtype=float)
                    for pixel in pixels:
                        x, y = np.rint(pixel).astype(int)
                        if not (0 <= x < width and 0 <= y < height and mask[y, x]):
                            raise ValueError("process landmark is outside the instance mask")
                    support = {**evidence, "points_world": [pixel_to_world(p, restored, calibration)[0].tolist() for p in pixels]}
                features = process_features(world_points, claim["category"], support=support)
            except ValueError as exc:
                ambiguities.append(f"{entity}: {exc}")
            points_ref = self.store.write("object-point-cloud", points)
            geometry_ref = self.store.write("observed-geometry", {**common, "process_features": features,
                "geometry_qualification": recovered.metadata.get("geometry_qualification", "unverified_estimate"),
                "coverage": "visible_surface", "source_refs": [points_ref, recovery_ref, recovery_metadata_ref, inference_ref],
                "raw_depth_ref": depth_ref, "mask_ref": mask_ref})
            # Sidecar is discoverable from the Nx3 artifact consumed by GraspNet.
            self.store.path(points_ref).with_suffix(".json").write_text(json.dumps({
                "geometry_ref": geometry_ref, "recovery_ref": recovery_ref,
                "recovery_metadata_ref": recovery_metadata_ref, **common}), encoding="utf-8")
            derived.append(artifact(points_ref, "object_point_cloud", {"point_count": len(points), "unit": "m"},
                                    [mask_ref, depth_ref], [rgb_ref, depth_ref]))
            # No spatial envelope/object_geometry confidence is invented for an
            # unqualified model estimate. Grasp Query accepts point clouds alone.
            records[entity] = {**common, "features": features, "world_from_camera": transform.tolist(),
                "points_ref": points_ref, "geometry_ref": geometry_ref,
                "geometry_qualification": recovered.metadata.get("geometry_qualification", "unverified_estimate"),
                "claim": claim, "artifacts": list(request["artifacts"])}
        self.observations[request["calibration_ref"]] = records
        output = {"entities": entities, "spatial_envelopes": envelopes, "derived_artifacts": derived,
            "relations": [], "ambiguities": [{"code": "visual_object_unresolved", "message": message,
                                               "entity_refs": []} for message in ambiguities]}
        self.store.write("understanding", {"request": request, "result": output})
        return output

    def _understand_simulator_truth(self, request, manifest):
        """Use authored scene labels/features while retaining capture lineage."""
        from .simulator_truth_perception import (
            object_point_cloud,
            process_feature_candidates_by_component,
            world_bounds_in_frame,
        )

        depth_ref = next((ref for ref in request["artifacts"]
                          if ref.startswith("artifact://labutopia/depth/")), None)
        point_cloud_ref = next((ref for ref in request["artifacts"]
                                if ref.startswith("artifact://labutopia/point_cloud/")), None)
        state_ref = next((ref for ref in request["artifacts"]
                          if ref.startswith("artifact://labutopia/state/")), None)
        if depth_ref is None or point_cloud_ref is None or state_ref is None:
            raise ValueError("simulator truth requires same-capture depth, point-cloud and USD state artifacts")
        calibration = json.loads(self.resolver.resolve(request["calibration_ref"]).data)
        if any(calibration[key] != request[key] for key in ("scene_revision", "frame_id")):
            raise ValueError("calibration does not belong to the capture")
        depth = np.load(io.BytesIO(self.resolver.resolve(depth_ref).data), allow_pickle=False)
        point_cloud = np.load(io.BytesIO(self.resolver.resolve(point_cloud_ref).data), allow_pickle=False)
        state = json.loads(self.resolver.resolve(state_ref).data)
        supported_schemas = {
            "labutopia-simulator-world-bounds/v1": "final_composed_usd_world_bounds",
            "labutopia-simulator-world-geometry/v1": "final_composed_usd_world_geometry",
        }
        if (state.get("schema") not in supported_schemas
                or state.get("scene_revision") != request["scene_revision"] or state.get("unit") != "m"
                or state.get("source") != supported_schemas.get(state.get("schema"))
                or not isinstance(state.get("objects"), list)):
            raise ValueError("simulator USD state does not match the observed scene revision")
        world_bounds = {}
        for item in state["objects"]:
            if not isinstance(item, dict) or not isinstance(item.get("label"), str) or item["label"] in world_bounds:
                raise ValueError("simulator USD state has missing or duplicate labels")
            spec = manifest["objects"].get(item["label"])
            if (spec is None or item.get("category") != spec["category"]
                    or item.get("prim_path") != spec["prim_path"]):
                raise ValueError("simulator USD state identity differs from the truth manifest")
            world_bounds[item["label"]] = item
        if depth.size == 0 or not np.isfinite(depth).any():
            raise ValueError("simulator truth depth artifact is empty or has no finite samples")
        identity = {key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        truth_ref = self.store.write("simulator-truth", {**identity, "manifest": manifest,
            "source_refs": [depth_ref, point_cloud_ref, state_ref], "depth_shape": list(depth.shape),
            "point_cloud_shape": list(point_cloud.shape)})
        entities, envelopes, derived, records, ambiguities = [], [], [], {}, []
        for label, spec in manifest["objects"].items():
            category = spec["category"]
            if category not in {"reagent_bottle", "mixing_vessel", "stir_tool", "test_tube"}:
                raise ValueError(f"unsupported simulator truth category: {category}")
            bounds = world_bounds.get(label)
            if bounds is None:
                entity = f"entity://simulator-truth-{label}"
                entities.append({"entity_ref": entity, "category": category, "label": label,
                                 "confidence": 1.0, "provenance": [depth_ref, point_cloud_ref]})
                ambiguities.append({
                    "code": "simulator_truth_geometry_unavailable",
                    "message": f"Final composed USD world bounds are unavailable for {label}",
                    "entity_refs": [entity],
                })
                continue
            points = object_point_cloud(calibration, point_cloud, bounds)
            if len(points) < 3:
                entity = f"entity://simulator-truth-{label}"
                entities.append({"entity_ref": entity, "category": category, "label": label,
                                 "confidence": 1.0, "provenance": [depth_ref, point_cloud_ref]})
                ambiguities.append({
                    "code": "simulator_truth_geometry_not_visible",
                    "message": f"No sufficient same-capture points fall inside final USD bounds for {label}",
                    "entity_refs": [entity],
                })
                continue
            points_ref = self.store.write("object-point-cloud", points)
            envelope_minimum, envelope_maximum = world_bounds_in_frame(calibration, bounds)
            entity = f"entity://simulator-truth-{label}"
            feature_candidates = []
            mesh_points = bounds.get("mesh_points_world_m")
            boundary_edges = bounds.get("boundary_edges_world_m")
            if state.get("schema") == "labutopia-simulator-world-geometry/v1" and category in {
                "reagent_bottle", "mixing_vessel", "stir_tool"
            }:
                try:
                    boundary_components = bounds.get("boundary_edge_components_world_m")
                    if boundary_components is None and boundary_edges is not None:
                        boundary_components = [boundary_edges]
                    feature_candidates = process_feature_candidates_by_component(
                        mesh_points,
                        boundary_components,
                        category,
                    )
                    if category == "stir_tool" and len(feature_candidates) > 1:
                        ambiguities.append({
                            "code": "simulator_truth_process_feature_ambiguous",
                            "message": f"Working-end role for {label} requires task/grasp-context selection",
                            "entity_refs": [entity],
                        })
                except (TypeError, ValueError) as exc:
                    ambiguities.append({
                        "code": "simulator_truth_process_feature_ambiguous",
                        "message": f"Process geometry for {label} is unavailable: {exc}",
                        "entity_refs": [entity],
                    })
            geometry_ref = self.store.write("observed-geometry", {
                **identity, "entity_ref": entity, "label": label, "category": category,
                "geometry_qualification": "simulator_ground_truth", "coverage": "simulator_visible_surface",
                "process_features": None,
                "process_feature_candidates": feature_candidates,
                "source_refs": [truth_ref, depth_ref, point_cloud_ref, state_ref, points_ref],
                "raw_depth_ref": depth_ref})
            self.store.path(points_ref).with_suffix(".json").write_text(json.dumps({
                "geometry_ref": geometry_ref, "truth_ref": truth_ref, **identity,
                "entity_ref": entity, "label": label, "category": category,
            }), encoding="utf-8")
            # Public Query provenance may only name request artifacts or
            # derived artifacts. Keep the manifest receipt in adapter-private
            # geometry evidence instead of widening the public source set.
            entities.append({"entity_ref": entity, "category": category, "label": label,
                             "confidence": 1.0, "provenance": [depth_ref, point_cloud_ref]})
            envelopes.append({
                "entity_ref": entity,
                "frame_id": request["frame_id"],
                "unit": "m",
                "min_xyz_m": envelope_minimum.tolist(),
                "max_xyz_m": envelope_maximum.tolist(),
                "confidence": 1.0,
                "provenance": [state_ref],
            })
            derived.append({"artifact_ref": points_ref, "kind": "object_point_cloud",
                            "media_type": "application/numpy", **identity, "entity_ref": entity,
                            "source_refs": [depth_ref, point_cloud_ref],
                            "provenance": [depth_ref, point_cloud_ref],
                            "descriptor": {"point_count": len(points), "unit": "m", "confidence": None,
                                           "width_px": None, "height_px": None, "bbox_xyxy_px": None,
                                           "foreground_pixels": None, "min_xyz_m": None, "max_xyz_m": None}})
            records[entity] = {**identity, "entity_ref": entity, "category": category, "label": label,
                "features": None, "process_feature_candidates": feature_candidates,
                "world_from_camera": world_from_camera(calibration).tolist(), "points_ref": points_ref,
                "geometry_ref": geometry_ref, "geometry_qualification": "simulator_ground_truth",
                "claim": {"category": category, "label": label, "identity_resolved": True},
                "artifacts": list(request["artifacts"]), "prim_path": spec["prim_path"]}
        self.observations[request["calibration_ref"]] = records
        output = {"entities": entities, "spatial_envelopes": envelopes, "derived_artifacts": derived,
                  "relations": [], "ambiguities": ambiguities}
        self.store.write("understanding", {"request": request, "result": output,
                                             "source": "simulator_authored_truth"})
        return output

    def _bind_execution(self, request, entities):
        if self.engine is None:
            raise ValueError("execution correspondence is unavailable in offline perception")
        records = self._records(request)
        capture = self.captures[request["calibration_ref"]][0]
        result = self.engine.bind_observed_entities({**capture, "claims": [
            {"entity_ref": entity, "points_ref": records[entity]["points_ref"]} for entity in entities]})
        if result.get("status") != "available" or len(result.get("records", [])) != len(entities):
            raise ValueError(f"execution correspondence unavailable: {result.get('failure_code')}")
        private = {record["entity_ref"]: record for record in result["records"]}
        if set(private) != set(entities):
            raise ValueError("execution correspondence changed perception identities")
        self.identities.setdefault(request["calibration_ref"], {}).update(private)
        self.capabilities[request["calibration_ref"]] = result["capabilities"]
        return private

    def _records(self, request):
        records = self.observations.get(request["calibration_ref"])
        if not records or any(record[key] != request[key] for record in records.values()
                              for key in ("scene_revision", "observation_ref", "frame_id", "calibration_ref")):
            raise ValueError("observed geometry does not match this capture")
        return records

    def describe(self, request):
        capture = self.captures.get(request["calibration_ref"])
        if capture is None or any(capture[0][key] != request[key] for key in
                                  ("scene_revision", "observation_ref", "calibration_ref")):
            raise ValueError("capabilities do not match the capture")
        if request["calibration_ref"] not in self.capabilities:
            self._bind_execution(capture[0], [])
        return deepcopy(self.capabilities[request["calibration_ref"]])

    def resolve(self, binding, request):
        records = self._records(binding)
        source = records[binding["entity_ref"]]
        destination_ref = "entity://" + binding["destination_ref"].removeprefix("destination://")
        destination = records[destination_ref]
        process_type = request.get("process_type")
        if process_type in {"pour", "stir"}:
            selected_refs = request.get("process_feature_refs")
            candidate_set_ref = request.get("process_feature_candidate_set_ref")
            if not isinstance(selected_refs, list) or not isinstance(candidate_set_ref, str):
                raise ValueError("planner-selected process feature refs are required")
            feature_request = {
                "entity_refs": [source["entity_ref"], destination_ref],
                "candidate_set_ref": candidate_set_ref,
                "selected_feature_refs": selected_refs,
                **{key: binding[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            }
            validation = self.validate_selection(feature_request)
            if validation.get("status") != "available":
                raise ValueError(validation.get("error", "selected process features are unavailable"))
        candidate = self.grasps.candidate(binding)
        if candidate["entity_ref"] != source["entity_ref"] or candidate["grasp_frame"]["frame_id"] != binding["frame_id"]:
            raise ValueError("selected prediction has a different entity or frame")
        transform = np.asarray(source["world_from_camera"])
        grasp, approach = candidate_world_pose(candidate, transform, self.provider_from_tcp)
        features = source["features"]
        if features is None or destination["features"] is None:
            raise ValueError("selected objects lack observed process features")
        if any(record["geometry_qualification"] not in {"validated_observation", "simulator_ground_truth"}
               for record in (source, destination)):
            raise ValueError("geometry estimates have not been validated for process preparation")
        private = self._bind_execution(binding, [source["entity_ref"], destination_ref])
        origin = np.asarray(features["origin_world"])
        def pose(position, rotation=(0., 0., 0., 1.)):
            return {"frame_id": "world", "unit": "m", "position_m": list(position), "orientation_xyzw": list(rotation)}
        return {**{key: binding[key] for key in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref", "candidate_ref")},
                "control_frame_id": "world", "world_from_control": {"parent_frame_id": "world", "child_frame_id": "world",
                    "translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
                "entity_prim_path": private[source["entity_ref"]]["prim_path"],
                "destination_prim_path": private[destination_ref]["prim_path"],
                "object_pose": pose(origin), "return_pose": pose(origin),
                "grasp_frame": pose(grasp[:3, 3], Rotation.from_matrix(grasp[:3, :3]).as_quat()),
                "approach_direction": {"frame_id": "world", "unit": "unitless", "vector": approach.tolist()},
                "destination_pose": pose(destination["features"]["origin_world"]),
                "tool_frame": {"frame_id": "observed_object", "tip_offset_m": (np.asarray(features["tip_world"]) - origin).tolist(),
                               "tip_axis_local": features["axis_world"]},
                "process_frame": {"frame_id": "world", "origin_m": destination["features"]["tip_world"],
                                  "axis": destination["features"]["axis_world"]},
                "geometry": {"size_m": features["size_m"]}}

    def propose(self, request):
        """Expose only opaque identities and semantic roles from the current capture."""
        records = self._records(request)
        expected = set(request["entity_refs"])
        if not expected <= set(records):
            raise ValueError("process feature Query entities do not belong to the current observation")
        candidates = []
        private_candidates = {}
        for entity_ref in request["entity_refs"]:
            record = records[entity_ref]
            for index, feature in enumerate(record.get("process_feature_candidates") or ()):
                role = feature.get("feature_role", "opening")
                feature_ref = f"process-feature://{uuid4().hex}"
                candidates.append({"feature_ref": feature_ref, "entity_ref": entity_ref,
                                   "feature_kind": feature.get("feature_kind", "unknown"),
                                   "feature_role": role})
                private_candidates[feature_ref] = (entity_ref, index, deepcopy(feature))
        candidate_set_ref = f"process-feature-set://{uuid4().hex}"
        self.process_feature_sets[candidate_set_ref] = {
            **{key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            "candidate_set_ref": candidate_set_ref,
            "entity_refs": tuple(request["entity_refs"]),
            "candidates": private_candidates,
        }
        return {
            "candidate_set_ref": candidate_set_ref,
            "observation_ref": request["observation_ref"],
            "scene_revision": request["scene_revision"], "frame_id": request["frame_id"],
            "calibration_ref": request["calibration_ref"], "candidates": candidates,
        }

    def validate_selection(self, request):
        """Bind selected refs to the current private capture before preparation."""
        identity = {key: request[key] for key in (
            "candidate_set_ref", "selected_feature_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )}
        records = self._records(request)
        expected_entities = set(request["entity_refs"])
        candidate_set = self.process_feature_sets.get(request.get("candidate_set_ref"))
        if candidate_set is None or any(candidate_set.get(key) != request[key] for key in (
            "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )) or set(candidate_set.get("entity_refs", ())) != expected_entities:
            return {"status": "stale", **identity, "error": "candidate set is not from the current process-feature Query"}
        selected = request["selected_feature_refs"]
        available = candidate_set["candidates"]
        for entity_ref in request["entity_refs"]:
            if entity_ref not in records:
                return {"status": "stale", **identity, "error": "selected entity is absent from the current capture"}
        if any(ref not in available for ref in selected):
            return {"status": "stale", **identity, "error": "selected refs are not in the current process-feature Query"}
        categories = {entity: records[entity].get("category") for entity in expected_entities}
        selected_entities = [available[ref][0] for ref in selected]
        if set(selected_entities) != expected_entities:
            return {"status": "ambiguous", **identity, "error": "selected features do not cover each task entity"}
        source_ref, destination_ref = request["entity_refs"]
        source_selected = [available[ref][2] for ref in selected if available[ref][0] == source_ref]
        destination_selected = [available[ref][2] for ref in selected if available[ref][0] == destination_ref]
        if request["operation"] == "pour" and (len(source_selected) != 1 or len(destination_selected) != 1):
            return {"status": "ambiguous", **identity, "error": "pour selects exactly one source rim and one destination rim"}
        if request["operation"] == "stir" and (len(source_selected) != 2 or len(destination_selected) != 1):
            return {"status": "ambiguous", **identity, "error": "stir selects both rod endpoints and one destination rim"}
        for ref in selected:
            entity, _index, feature = available[ref]
            kind = feature.get("feature_kind")
            category = categories[entity]
            if category in {"reagent_bottle", "mixing_vessel"} and kind != "rim":
                return {"status": "invalid", **identity, "error": "vessel operation requires a rim candidate"}
            if category == "stir_tool" and kind != "rod_endpoint_pair":
                return {"status": "invalid", **identity, "error": "stir operation requires a rod endpoint candidate"}
        if request["operation"] == "stir":
            roles = {available[ref][2].get("feature_role") for ref in selected if available[ref][0] == source_ref}
            if roles != {"endpoint_a", "endpoint_b"}:
                return {"status": "ambiguous", **identity, "error": "stir requires distinct endpoint_a and endpoint_b candidates"}
        return {"status": "available", **identity, "selected_feature_refs": list(selected)}

    def refresh_process(self, arguments, target, *, observation_model, phase_route):
        records = self._records(arguments)
        source = records[arguments["entity_ref"]]
        destination_ref = "entity://" + arguments["destination_ref"].removeprefix("destination://")
        destination = records[destination_ref]
        if any(record["features"] is None or record["geometry_qualification"] not in
               {"validated_observation", "simulator_ground_truth"}
               for record in (source, destination)):
            raise ValueError("held preparation requires current source and destination feature evidence")
        # Keep the acquisition geometry/candidate as historical evidence. Physics
        # feedback transports that established frame; it never estimates a tip.
        if not observation_model.get("geometry_ref") or "body_from_observed" not in phase_route:
            raise ValueError("held source has no established acquisition frame")
        private = self._bind_execution(arguments, [source["entity_ref"], destination_ref])
        if (private[source["entity_ref"]]["prim_path"] != target["entity_prim_path"]
                or private[destination_ref]["prim_path"] != target["destination_prim_path"]):
            raise ValueError("current observed identities do not match the held assignment")
        model_pose = np.asarray(private[source["entity_ref"]]["captured_body_pose"]) @ np.asarray(phase_route["body_from_observed"])
        local_from_world = np.linalg.inv(model_pose)
        features = source["features"]
        local_tip = local_from_world[:3, :3] @ np.asarray(features["tip_world"]) + local_from_world[:3, 3]
        local_axis = local_from_world[:3, :3] @ np.asarray(features["axis_world"])
        updated = deepcopy(target)
        updated["tool_frame"] = {"frame_id": "observed_object", "tip_offset_m": local_tip.tolist(),
                                 "tip_axis_local": local_axis.tolist()}
        updated["process_frame"] = {"frame_id": "world", "origin_m": destination["features"]["tip_world"],
                                    "axis": destination["features"]["axis_world"]}
        updated.update({key: arguments[key] for key in ("scene_revision", "frame_id", "calibration_ref")})
        return updated

    def execution_context(self, binding):
        source = self._records(binding)[binding["entity_ref"]]
        return {"points_ref": source["points_ref"], "world_from_camera": source["world_from_camera"],
                "captured_body_pose": self.identities[binding["calibration_ref"]][binding["entity_ref"]]["captured_body_pose"],
                "observation_ref": binding["observation_ref"], "geometry_ref": source["geometry_ref"]}

    def close(self):
        try:
            if self.segmentation is not None:
                self.segmentation.shutdown()
        finally:
            try:
                if self.geometry is not None:
                    self.geometry.shutdown()
            finally:
                self.grasps.close()
