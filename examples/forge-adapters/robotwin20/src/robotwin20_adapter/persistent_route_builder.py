"""Materialize current-scene candidates using the existing no-motion CLI."""

from __future__ import annotations

import json
import math
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Mapping

from PhyAgentOS.forge.manipulation import ManipulationIntent

from .arm_candidates import enumerate_arm_candidates, load_arm_planning_profile
from .route_inputs import validate_scene_facts
from .route_readiness import validate_route_request


class BenchmarkSceneSource:
    """Explicit simulator-facts source; never a substitute for model perception."""

    def __init__(self, client):
        self.client = client

    def __call__(self, request):
        response = self.client.query("benchmark_scene_facts", {"calibration_ref": request["calibration_ref"]})
        for key in ("holding_state", "owner", "acquire_invocation_id", "entity_ref"):
            response.pop(key, None)
        return validate_scene_facts(response)


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

    def _current(self, scene_revision):
        current = self.client.query("snapshot", {})
        if current["scene_revision"] != scene_revision or current["holding_state"] != "empty":
            raise ValueError("route building requires the current empty scene")

    def build(self, request: Mapping[str, Any]) -> dict[str, Any]:
        intent = ManipulationIntent.model_validate(request["intent"])
        self._current(intent.scene_revision)
        # Validate the candidate/arm budget before invoking an expensive materializer.
        enumerate_arm_candidates(intent, request["candidates"], self.arm_profile)
        facts = validate_scene_facts(self.scene_source(deepcopy(dict(request))))
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
        output_roots = []
        for index, candidate in enumerate(request["candidates"]):
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
                subprocess.run(argv, check=True, timeout=self.timeout_s, stdout=log, stderr=subprocess.STDOUT)
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
            output_roots.append(output)
        self._current(intent.scene_revision)
        assert base is not None
        base["candidates"] = candidates
        validate_route_request(base)
        options = enumerate_arm_candidates(intent, candidates, self.arm_profile)
        self._import_artifacts(output_roots)
        return {"destination_ref": request["destination_ref"], "base_request": base, "options": options}

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
