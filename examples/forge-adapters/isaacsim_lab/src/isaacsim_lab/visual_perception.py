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


class RecordedGraspProvider:
    """Persist actual model inputs/output and capture-specific candidate refs."""

    def __init__(self, provider, store):
        self.provider, self.store = provider, store
        self.captures = {}

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
        self.captures.setdefault(request["calibration_ref"], {}).update({i["candidate_ref"]: deepcopy(i) for i in candidates})
        return output

    def candidate(self, binding):
        item = self.captures.get(binding["calibration_ref"], {}).get(binding["candidate_ref"])
        if item is None or dict(item) != dict(binding["grasp_candidate"]):
            raise ValueError("selected grasp differs from the model prediction for this capture")
        return item

    def close(self):
        self.provider.release()


class LabVisualPerception:
    """Compose existing segmentation/localization Providers; no grasp synthesis.

    Observed geometry and private execution correspondence are separate stores.
    Only RGB-D-derived artifacts are published through scene.understand.
    """

    def __init__(self, engine, artifact_resolver, inference, *, segmentation, geometry, store, grasps, provider_from_tcp):
        from robotwin20_adapter.single_view_perception import NumpyMetricLocalizationProvider
        self.engine, self.resolver, self.inference = engine, artifact_resolver, inference
        self.segmentation, self.store, self.grasps = segmentation, store, grasps
        self.geometry = geometry
        self.localization = NumpyMetricLocalizationProvider(depth_scale_to_m=1.)
        self.provider_from_tcp = np.asarray(provider_from_tcp, dtype=float)
        if (self.provider_from_tcp.shape != (4, 4) or not np.isfinite(self.provider_from_tcp).all()
                or not np.allclose(self.provider_from_tcp[3], [0, 0, 0, 1])
                or not np.allclose(self.provider_from_tcp[:3, :3].T @ self.provider_from_tcp[:3, :3], np.eye(3))
                or np.linalg.det(self.provider_from_tcp[:3, :3]) < 0):
            raise ValueError("provider_from_tcp must be a rigid calibrated transform")
        self.observations, self.identities, self.capabilities = {}, {}, {}
        self.captures, self.labels = {}, {}
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
        candidate = self.grasps.candidate(binding)
        if candidate["entity_ref"] != source["entity_ref"] or candidate["grasp_frame"]["frame_id"] != binding["frame_id"]:
            raise ValueError("selected prediction has a different entity or frame")
        transform = np.asarray(source["world_from_camera"])
        grasp, approach = candidate_world_pose(candidate, transform, self.provider_from_tcp)
        features = source["features"]
        if features is None or destination["features"] is None:
            raise ValueError("selected objects lack observed process features")
        if any(record["geometry_qualification"] != "validated_observation" for record in (source, destination)):
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

    def refresh_process(self, arguments, target, *, observation_model, phase_route):
        records = self._records(arguments)
        source = records[arguments["entity_ref"]]
        destination_ref = "entity://" + arguments["destination_ref"].removeprefix("destination://")
        destination = records[destination_ref]
        if any(record["features"] is None or record["geometry_qualification"] != "validated_observation"
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
            self.segmentation.shutdown()
        finally:
            try:
                self.geometry.shutdown()
            finally:
                self.grasps.close()
