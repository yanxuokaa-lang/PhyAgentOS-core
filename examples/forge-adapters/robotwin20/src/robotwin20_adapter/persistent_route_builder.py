"""Materialize current-scene candidates using the existing no-motion CLI."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic
from typing import Any, Mapping

from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError
from PhyAgentOS.forge.manipulation import ManipulationIntent

from .arm_candidates import enumerate_arm_candidates, load_arm_planning_profile
from .preparation_deadline import PreparationDeadline, PreparationDeadlineExceededError
from .route_evidence import _artifact_path
from .route_inputs import canonical_json, validate_scene_facts
from .route_readiness import route_geometry_digest, validate_route_request


class BenchmarkSceneSource:
    """Execution geometry only; legacy class name retained for host compatibility."""

    def __init__(self, client):
        self.client = client

    def __call__(self, request, *, deadline: PreparationDeadline | None = None):
        kwargs = {} if deadline is None else {
            "timeout_s": deadline.remaining("execution_scene_facts")
        }
        response = self.client.query(
            "execution_scene_facts", {"calibration_ref": request["calibration_ref"]}, **kwargs
        )
        for key in ("holding_state", "owner", "acquire_invocation_id", "entity_ref", "ok", "request_id"):
            response.pop(key, None)
        return response


class PersistentRouteBuilder:
    """Own build directories; never create execution approval.

    scene_source(request) supplies measured, source-bound scene facts. Benchmark
    introspection must be explicitly configured by the deployment. command is
    the Python interpreter plus the existing materialize_complete_route.py CLI;
    materializer_arguments contains its static profile/qualification arguments.
    """

    def __init__(self, *, client, artifact_root: Path, scene_source, command,
                 materializer_arguments: Mapping[str, str], timeout_s: float = 120):
        self.client = client
        self.root = artifact_root.resolve()
        self.scene_source = scene_source
        self.command = tuple(command)
        self.arguments = dict(materializer_arguments)
        self.timeout_s = timeout_s
        if not self.command or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("materializer command and finite positive timeout are required")
        reserved = {"scene-facts", "source-capture-root", "grasp-results", "artifact-root",
                    "candidate-ref", "entity-ref", "request-id"}
        if reserved & self.arguments.keys():
            raise ValueError("materializer configuration overrides dynamic scene arguments")
        self.arm_profile = load_arm_planning_profile(Path(self.arguments["arm-planning-profile"]))

    def _current(self, scene_revision, *, deadline: PreparationDeadline | None = None):
        kwargs = {} if deadline is None else {
            "timeout_s": deadline.remaining("route_snapshot")
        }
        current = self.client.query("snapshot", {}, **kwargs)
        if current["scene_revision"] != scene_revision or current["holding_state"] != "empty":
            raise ValueError("route building requires the current empty scene")

    def build(
        self,
        request: Mapping[str, Any],
        *,
        deadline: PreparationDeadline | None = None,
        metrics: dict[str, Any] | None = None,
        _nominal_only: bool = False,
    ) -> dict[str, Any]:
        intent = ManipulationIntent.model_validate(request["intent"])
        if deadline is not None:
            deadline.remaining("route_materialization")
        self._current(intent.scene_revision, deadline=deadline)
        # Validate the candidate/arm budget before invoking an expensive materializer.
        enumerate_arm_candidates(intent, request["candidates"], self.arm_profile)
        source_kwargs = {} if deadline is None else {"deadline": deadline}
        facts = validate_scene_facts(self.scene_source(deepcopy(dict(request)), **source_kwargs))
        for key in ("scene_revision", "observation_ref", "calibration_ref"):
            if facts[key] != request[key]:
                raise ValueError(f"route scene facts differ from request: {key}")
        if facts["observation_frame_id"] != request["frame_id"]:
            raise ValueError("route scene facts observation frame differs from request")
        target = next((item for item in facts["objects"] if item["entity_ref"] == intent.entity_ref), None)
        if target is None or target["target_ref"] != request["destination_ref"]:
            raise ValueError("requested destination is not grounded in current scene facts")
        runs = self.root / "preparation-builds"
        runs.mkdir(parents=True, exist_ok=True)
        run = Path(mkdtemp(prefix="route-", dir=runs))
        (run / "scene-facts.json").write_text(json.dumps(facts), encoding="utf-8")
        bundle = {"request": {key: request[key] for key in (
            "observation_ref", "scene_revision", "frame_id", "calibration_ref",
        )}, "result": {"candidates": request["candidates"]}}
        (run / "grasp-results.json").write_text(json.dumps(bundle), encoding="utf-8")
        base = None
        candidates = []
        reviews = {}
        output_roots = []
        for index, candidate in enumerate(request["candidates"]):
            if deadline is not None:
                deadline.remaining("route_materialization")
            output = run / f"candidate-{index}"
            output.mkdir()
            arguments = {**self.arguments, "scene-facts": str(run / "scene-facts.json"),
                         "source-capture-root": str(self.root), "grasp-results": str(run / "grasp-results.json"),
                         "artifact-root": str(output), "candidate-ref": candidate["candidate_ref"],
                         "entity-ref": intent.entity_ref, "request-id": f"{run.name}-{index}"}
            argv = [*self.command]
            for key, value in arguments.items():
                argv.extend((f"--{key}", str(value)))
            (run / f"command-{index}.json").write_text(json.dumps(argv), encoding="utf-8")
            with (run / f"materializer-{index}.log").open("w", encoding="utf-8") as log:
                timeout_s = (
                    self.timeout_s
                    if deadline is None
                    else deadline.bounded_timeout(
                        self.timeout_s,
                        "route_materialization",
                    )
                )
                try:
                    materialization_started = monotonic()
                    subprocess.run(
                        argv,
                        check=True,
                        timeout=timeout_s,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise PreparationDeadlineExceededError(
                        "preparation timed out during route materialization"
                    ) from exc
                except subprocess.CalledProcessError as exc:
                    diagnostic_path = output / "materialization_error.json"
                    try:
                        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        diagnostic = {}
                    code = diagnostic.get("code") if isinstance(diagnostic, dict) else None
                    message = diagnostic.get("message") if isinstance(diagnostic, dict) else None
                    if not isinstance(code, str) or not code or not isinstance(message, str) or not message:
                        code = "route_materialization_failed"
                        message = f"Route materializer exited with status {exc.returncode}"
                    if code == "route_candidate_rejected":
                        if metrics is not None:
                            metrics.setdefault("materialization_rejections", []).append({
                                "candidate_ref": candidate["candidate_ref"], "code": code, "message": message,
                                "diagnostic_ref": f"preparation-builds/{run.name}/candidate-{index}/materialization_error.json",
                            })
                        continue
                    raise PreparationProviderError(
                        code,
                        f"{message}; diagnostic log: preparation-builds/{run.name}/materializer-{index}.log",
                    ) from exc
                finally:
                    if metrics is not None:
                        metrics.setdefault("materialization", []).append(
                            {
                                "candidate_ref": candidate["candidate_ref"],
                                "elapsed_s": monotonic() - materialization_started,
                            }
                        )
            route = json.loads((output / "route_request.json").read_text(encoding="utf-8"))
            validate_route_request(route)
            for key in ("scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref"):
                if route[key] != request[key]:
                    raise ValueError(f"materialized route source mismatch: {key}")
            if len(route["candidates"]) != 1:
                raise ValueError("materializer must return the requested candidate")
            generated = route["candidates"][0]
            if (generated["candidate_ref"] != candidate["candidate_ref"]
                    or generated["entity_ref"] != intent.entity_ref
                    or generated["placement_target"]["target_ref"] != request["destination_ref"]):
                raise ValueError("materialized candidate or destination mismatch")
            base = route if base is None else base
            candidates.append(generated)
            reviews[candidate["candidate_ref"]] = str(output / "human_review_request.json")
            output_roots.append(output)
        self._current(intent.scene_revision, deadline=deadline)
        if deadline is not None:
            deadline.remaining("route_materialization")
        if base is None:
            raise PreparationProviderError(
                "no_materializable_candidates",
                f"All candidates were rejected during route construction; diagnostics: preparation-builds/{run.name}",
            )
        base["candidates"] = candidates
        validate_route_request(base)
        options = enumerate_arm_candidates(intent, candidates, self.arm_profile)
        self._import_artifacts(output_roots)
        result = {"destination_ref": request["destination_ref"], "base_request": base,
                  "options": options, "reviews": reviews}
        if facts.get("geometry_source") == "observation" and not _nominal_only:
            return self._qualify_contacts(request, result, run, deadline, metrics)
        return result

    def _qualify_contacts(self, request, bundle, run, deadline, metrics):
        """Qualify nominal grasps, then regenerate all dependent route geometry."""
        deadline = deadline or PreparationDeadline.start(self.timeout_s)
        from collections import Counter

        qualified = {}
        reviews, options = {}, []
        rejections = Counter()
        base = None
        for index, candidate in enumerate(bundle["base_request"]["candidates"]):
            route = {**bundle["base_request"], "candidates": [candidate]}
            timeout = deadline.remaining("contact_qualification")
            started = monotonic()
            response = self.client.query("contact_qualification", {
                "route_request": route, "allowed_arms": request["intent"]["allowed_arms"],
                "timeout_s": timeout}, timeout_s=timeout)
            result = response["candidates"][candidate["candidate_ref"]]
            diagnostic = run / f"contact-{index}.json"
            diagnostic.write_text(json.dumps(result), encoding="utf-8")
            diagnostic_ref = f"artifact://preparation-builds/{run.name}/contact-{index}"
            if metrics is not None:
                metrics.setdefault("contact_qualification", []).append({
                    "candidate_ref": candidate["candidate_ref"], "status": result["status"],
                    "elapsed_s": monotonic() - started, "evidence_ref": diagnostic_ref})
            deadline.remaining("contact_qualification")
            for attempt in result.get("arm_attempts", []):
                for variant in attempt["qualification"]["variants"]:
                    rejections.update(variant["rejection_reasons"])
            if result["status"] != "qualified":
                continue
            if (result.get("scene_revision") != route["scene_revision"]
                    or result.get("candidate_ref") != candidate["candidate_ref"]
                    or result.get("arm_id") not in request["intent"]["allowed_arms"]
                    or result.get("motion_authorized") is not False):
                raise ValueError("contact qualification does not bind the current candidate and arm")
            raw = next(c for c in request["candidates"] if c["candidate_ref"] == candidate["candidate_ref"])
            for attempt in result["arm_attempts"]:
                arm, value = attempt["arm_id"], attempt["qualification"]
                if value["status"] != "qualified":
                    continue
                if arm not in request["intent"]["allowed_arms"]:
                    raise ValueError("qualified arm is not allowed by the manipulation intent")
                qualification = run / f"qualification-{index}-{arm}.json"
                qualification.write_text(json.dumps(value), encoding="utf-8")
                child = PersistentRouteBuilder(client=self.client, artifact_root=self.root,
                    scene_source=self.scene_source, command=self.command, timeout_s=self.timeout_s,
                    materializer_arguments={**self.arguments, "contact-qualification": str(qualification),
                        "contact-qualification-ref": f"artifact://preparation-builds/{run.name}/qualification-{index}-{arm}"})
                try:
                    rebuilt = child.build({**request, "candidates": [raw]}, deadline=deadline,
                                          metrics=metrics, _nominal_only=True)
                except PreparationProviderError as exc:
                    if exc.code != "no_materializable_candidates":
                        raise
                    continue
                base = rebuilt["base_request"] if base is None else base
                generated = rebuilt["base_request"]["candidates"][0]
                qualified.setdefault(candidate["candidate_ref"], generated)
                # Different arms may need different backoffs for the same raw
                # proposal. Full readiness, not this prefix, chooses the arm.
                reviews[generated["execution_grasp"]["adaptation_provenance_ref"]] = rebuilt["reviews"][candidate["candidate_ref"]]
                for option in rebuilt["options"]:
                    if option["arm_ids"] == [arm]:
                        options.append({**option, "option_id": f"qualified-{index}-{arm}"})
        if base is None:
            raise PreparationProviderError("no_qualified_contacts",
                f"No observed candidate passed contact qualification and route construction: {dict(rejections)}; "
                f"diagnostics: artifact://preparation-builds/{run.name}")
        base["candidates"] = list(qualified.values())
        return {"destination_ref": request["destination_ref"], "base_request": base,
                "options": options, "reviews": reviews}

    def finalize(
        self,
        bundle,
        route,
        *,
        deadline: PreparationDeadline | None = None,
    ):
        """Bind existing review evidence to the selected request without approving it."""
        if deadline is not None:
            deadline.remaining("route_finalization")
        validate_route_request(route)
        self._current(route["scene_revision"], deadline=deadline)
        candidate = route["candidates"][0]
        if len(route["candidates"]) != 1:
            raise ValueError("finalization requires one selected candidate")
        review_key = candidate["execution_grasp"].get("adaptation_provenance_ref")
        review_path = Path(bundle["reviews"].get(review_key) or bundle["reviews"][candidate["candidate_ref"]])
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if (review["candidate_ref"] != candidate["candidate_ref"]
                or review["scene_revision"] != route["scene_revision"]
                or review["motion_authorized"] is not False
                or review["decision"] != "pending_human_review"):
            raise ValueError("source review does not bind the selected candidate")
        manifest_bytes = _artifact_path(self.root, review["source_manifest_ref"]).read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != review["source_manifest_sha256"]:
            raise ValueError("source manifest differs from materializer review")
        manifest = json.loads(manifest_bytes)
        prefix = f"artifact://selected-routes/{route['request_id']}"

        def write(ref, value):
            relative = ref.removeprefix("artifact://")
            path = self.root / (relative + ".json")
            if self.root not in path.resolve().parents:
                raise ValueError("selected route artifact escapes runtime root")
            data = canonical_json(value)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if path.is_symlink() or path.read_bytes() != data:
                    raise ValueError("selected route artifact already identifies different content")
            else:
                with path.open("xb") as stream:
                    stream.write(data)
            return hashlib.sha256(data).hexdigest()

        route_ref = f"{prefix}/route-request"
        route_sha = write(route_ref, route)
        manifest.update(request_id=route["request_id"],
                        route_request={"artifact_ref": route_ref, "sha256": route_sha},
                        route_geometry_digest=route_geometry_digest(route),
                        motion_capabilities=route["motion_capabilities"],
                        controller_qualification=route["controller_qualification"],
                        collision_world={key: route["collision_world"][key]
                                         for key in ("artifact_ref", "sha256", "world_digest")})
        manifest_ref = f"{prefix}/source-manifest"
        manifest_sha = write(manifest_ref, manifest)
        review.update(request_id=route["request_id"], route_geometry_digest=route_geometry_digest(route),
                      route_request_sha256=route_sha, source_manifest_ref=manifest_ref,
                      source_manifest_sha256=manifest_sha)
        for field, ref in (("calibration_sha256", route["calibration_ref"]),
                           ("joint_limits_sha256", route["joint_limits_ref"]),
                           ("stop_policy_sha256", route["stop_policy_ref"])):
            review[field] = hashlib.sha256(_artifact_path(self.root, ref).read_bytes()).hexdigest()
        review_ref = f"{prefix}/review-request"
        write(review_ref, review)
        if deadline is not None:
            deadline.remaining("route_finalization")
        return review_ref

    def _import_artifacts(self, output_roots):
        # References span shared calibration and per-route artifacts. Compare all
        # collisions before publishing any file, so a conflict never overwrites evidence.
        pending = {}
        for output in output_roots:
            for source in output.rglob("*"):
                if source.is_symlink():
                    raise ValueError("materializer output contains a symbolic link")
                if not source.is_file() or source.parent == output:
                    continue
                destination = self.root / source.relative_to(output)
                if self.root not in destination.resolve().parents:
                    raise ValueError("materializer artifact escapes runtime root")
                data = source.read_bytes()
                if destination in pending and pending[destination] != data:
                    raise ValueError("materialized artifacts conflict across candidates")
                if destination.exists() and (destination.is_symlink() or destination.read_bytes() != data):
                    raise ValueError("materialized artifact conflicts with runtime evidence")
                pending[destination] = data
        for destination, data in pending.items():
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(data)
