"""Replay persisted observation geometry and real readiness in an isolated world.

Build and evaluate with PAOS; evaluation launches an isolated RoboTwin worker.
Neither mode connects to the live Gateway or changes a persisted AgentTask.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from time import monotonic


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def build(args):
    import yaml

    from robotwin20_adapter.grounding import Grounding
    from robotwin20_adapter.observed_support import SupportEstimationPolicy
    from robotwin20_adapter.persistent_route_builder import PersistentRouteBuilder
    from robotwin20_adapter.preparation_deadline import PreparationDeadline
    from robotwin20_adapter.route_evidence import _artifact_path

    root = Path(tempfile.mkdtemp(prefix="observed-prepare-", dir=args.output_parent)).resolve()
    source = args.source_root.resolve()
    argv = json.loads(args.materializer_command.read_text())
    profile = yaml.safe_load(Path(argv[argv.index("--route-input-profile") + 1]).read_text())
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        task = json.loads(conn.execute("SELECT record_json FROM agent_tasks WHERE task_id=?", (args.task_id,)).fetchone()[0])
    records = [r for rev in task["revisions"] for r in rev["execution_records"]]
    request = deepcopy(next(r["arguments"] for r in reversed(records) if r["tool_id"] == "manipulation.prepare"))
    target = json.loads(_artifact_path(source, request["destination_ref"].replace("destination://", "artifact://", 1)).read_text())
    binding = json.loads(_artifact_path(source, target["binding_ref"]).read_text())
    identity = {k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")}
    # Only copy the referenced capture directory; immutable calibration and all
    # perception outputs remain byte-for-byte inputs, not regenerated truth.
    calibration = _artifact_path(source, identity["calibration_ref"])
    capture = calibration.parent
    shutil.copytree(capture, root / capture.relative_to(source))
    capability = _artifact_path(source, request["capability_snapshot_ref"])
    (root / capability.relative_to(source)).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(capability, root / capability.relative_to(source))

    class SavedSceneClient:
        def query(self, operation, arguments, **kwargs):
            if operation not in {"snapshot", "bind_observed_entities"}:
                raise ValueError("replay cannot call a live Tool")
            return {"scene_revision": request["scene_revision"], "holding_state": "empty", "scene_validity": "action_driven"}

    client = SavedSceneClient()
    grounding = Grounding(client, root, lambda _: deepcopy(binding["scene_facts"]),
                          support_policy=SupportEstimationPolicy(**profile.get("observed_support", {})))
    for tool in ("scene.observe", "scene.understand"):
        result = next(r["response"]["data"] for r in reversed(records)
                      if r["tool_id"] == tool and r["response"]["data"].get("scene_revision") == identity["scene_revision"])
        grounding.remember(tool, result)
    bound = grounding.bind({**identity, "entity_refs": list(binding["objects"])})
    target_request = {**target["requested_pose"], "binding_ref": bound["binding_ref"]}
    destination = grounding.target(target_request)
    request["destination_ref"] = destination["destination_ref"]
    arguments = dict(zip((x.removeprefix("--") for x in argv[2::2]), argv[3::2]))
    for key in ("scene-facts", "source-capture-root", "grasp-results", "artifact-root", "candidate-ref", "entity-ref", "request-id"):
        arguments.pop(key)
    if args.limit is not None:
        request["candidates"] = request["candidates"][:args.limit]
    builder = PersistentRouteBuilder(client=client, artifact_root=root, scene_source=grounding.scene_facts,
                                     command=(sys.executable, str(Path(__file__).with_name("materialize_complete_route.py"))),
                                     materializer_arguments=arguments, timeout_s=300)
    metrics = {}
    start = monotonic()
    # Offline stage contains nominal materialization only. Runtime-dependent
    # contact qualification runs in evaluate, under the same preparation budget.
    bundle = builder.build(request, deadline=PreparationDeadline.start(args.deadline), metrics=metrics,
                           _nominal_only=True)
    write(root / "bundle.json", bundle)
    write(root / "request.json", request)
    write(root / "replay.json", {"task_id": args.task_id, "source_root": str(source), "source_binding": target["binding_ref"],
                                "binding_ref": bound["binding_ref"], "candidate_count": len(request["candidates"]),
                                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                                "working_tree_diff": subprocess.check_output(["git", "diff"], text=True),
                                "materializer_command": argv, "metrics": metrics, "build_s": monotonic() - start,
                                "gateway_calls": 0, "motion_authorized": False})
    print(root)


def evaluate(args):
    from robotwin20_adapter.arm_candidates import CompleteRouteSelector, load_arm_planning_profile
    from robotwin20_adapter.persistent_client import (
        PersistentWorkerClient,
        build_persistent_route_readiness,
    )
    from robotwin20_adapter.persistent_preparation import PersistentPreparationProvider
    from robotwin20_adapter.persistent_route_builder import PersistentRouteBuilder
    from robotwin20_adapter.prepared_routes import PreparedRoutes
    from robotwin20_adapter.process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
    from robotwin20_adapter.route_readiness import RouteReadinessEvaluationAdapter

    source = args.replay_root.resolve()
    root = Path(tempfile.mkdtemp(prefix="observed-readiness-", dir=source.parent))
    shutil.copytree(source, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
        "simulation-route-readiness", "preparation-rejections", "preparation-metrics", "readiness-summary.json"))
    print(root, flush=True)
    info = json.loads((root / "replay.json").read_text())
    request = json.loads((root / "request.json").read_text())
    bundle = json.loads((root / "bundle.json").read_text())
    profile = json.loads(args.runtime_profile.read_text())
    profile.update(artifact_root=str(root), stop_file=str(root / "stop"), video={"enabled": False, "fps": 25., "stride_steps": 4})
    adapter = Path(__file__).resolve().parents[1]
    snapshot = root / "source"
    for directory in ("src", "runtime", "scripts"):
        shutil.copytree(adapter / directory, snapshot / directory,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"))
    worker = JsonlProcessWorkerClient(ProcessWorkerConfig(
        command=(str(args.runtime_python), str(snapshot / "scripts" / Path(__file__).name), "worker", "--replay-root", str(root),
                 "--runtime-profile", str(args.runtime_profile.resolve())),
        environment={"PYTHONPATH": f"{snapshot / 'src'}:{snapshot / 'runtime'}"},
        startup_timeout_s=180, request_timeout_s=args.deadline, max_line_bytes=8_388_608,
    ))
    client = PersistentWorkerClient(worker)
    result = {"gateway_calls": 0, "motion_authorized": False, "simulator_steps": None,
              "runtime_profile": profile, "reset_before_readiness": True, "build_root": str(source),
              "runtime_python": str(args.runtime_python), "deadline_s": args.deadline,
              "source_snapshot": str(snapshot), "runtime_profile_contents": Path(profile["runtime_profile"]).read_text()}
    start = monotonic()
    try:
        client.query("bind_observed_entities", {"binding_ref": info["binding_ref"]})

        argv = info["materializer_command"]
        arguments = dict(zip((x.removeprefix("--") for x in argv[2::2]), argv[3::2]))
        for key in ("scene-facts", "source-capture-root", "grasp-results", "artifact-root", "candidate-ref", "entity-ref", "request-id"):
            arguments.pop(key)
        facts = json.loads(next((root / "preparation-builds").glob("*/scene-facts.json")).read_text())
        builder = PersistentRouteBuilder(client=client, artifact_root=root,
            scene_source=lambda request, **kwargs: deepcopy(facts),
            command=(sys.executable, str(snapshot / "scripts/materialize_complete_route.py")),
            materializer_arguments=arguments, timeout_s=args.deadline)
        qualification_run = root / "preparation-builds" / "contact-qualification"
        qualification_run.mkdir()

        class Builder:
            def build(self, *args, **kwargs):
                return builder._qualify_contacts(request, deepcopy(bundle), qualification_run,
                                                kwargs.get("deadline"), kwargs.get("metrics"))

            def finalize(self, *args, **kwargs):
                raise RuntimeError("replay does not publish execution approval")

        argv = info["materializer_command"]
        arm_profile = Path(argv[argv.index("--arm-planning-profile") + 1])
        provider = PersistentPreparationProvider(client=client, route_builder=Builder(),
                    selector=CompleteRouteSelector(RouteReadinessEvaluationAdapter(build_persistent_route_readiness(client)), load_arm_planning_profile(arm_profile)),
                    prepared_routes=PreparedRoutes(client, root), timeout_s=args.deadline)
        metrics = {}
        try:
            provider.prepare(request, metrics=metrics)
        except Exception as exc:
            result["outcome"] = {"type": type(exc).__name__, "code": getattr(exc, "code", None), "message": str(exc)}
        finally:
            result["metrics"] = metrics
    except Exception as exc:
        result["initialization_error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        try:
            snapshot_state = client.query("snapshot", {})
            result["simulator_steps"] = snapshot_state["replay_readiness_step_calls"]
        except Exception as exc:
            result["step_measurement_error"] = str(exc)
        client.close()
        result["worker_stderr_tail"] = list(worker._stderr_tail)
        result["total_s"] = monotonic() - start
        write(root / "readiness-summary.json", result)


def run_worker(args):
    from contextlib import redirect_stdout

    from robotwin_persistent_engine import RoboTwinPersistentEngine
    from worker_protocol import serve

    from robotwin20_adapter.persistent_manipulation import PersistentManipulationProvider

    root = args.replay_root.resolve()
    request = json.loads((root / "request.json").read_text())
    profile = json.loads(args.runtime_profile.read_text())
    profile.update(artifact_root=str(root), stop_file=str(root / "stop"), video={"enabled": False, "fps": 25., "stride_steps": 4})
    engine = None
    provider = None
    step_calls = 0

    def forbid_readiness_step(*args, **kwargs):
        nonlocal step_calls
        step_calls += 1
        raise RuntimeError("no-motion replay cannot step the simulator after initialization")

    def factory():
        nonlocal engine
        engine = RoboTwinPersistentEngine(profile)
        # Logical replay identity only. Never teleport actors to fit observations.
        engine.backend._scene_revision = request["scene_revision"]
        engine.backend._task.scene.step = forbid_readiness_step
        return engine

    def load():
        nonlocal provider
        with redirect_stdout(sys.stderr):
            provider = PersistentManipulationProvider(factory)

    def handle(payload):
        operation = payload.get("operation")
        if payload.get("command") != "query" or operation not in {"bind_observed_entities", "snapshot", "route_readiness", "contact_qualification"}:
            raise ValueError("no-motion replay permits only binding, snapshot and readiness")
        try:
            with redirect_stdout(sys.stderr):
                result = provider.query(operation, payload.get("arguments", {}))
            return {**result, "request_id": payload["request_id"], "ok": True,
                    "replay_readiness_step_calls": step_calls}
        except Exception as exc:
            return {"request_id": payload["request_id"], "ok": False,
                    "error": {"code": type(exc).__name__, "message": str(exc)}}

    try:
        serve("observed-preparation-replay", load, handle)
    finally:
        if provider is not None:
            with redirect_stdout(sys.stderr):
                provider.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("build")
    for name in ("database", "source-root", "materializer-command", "output-parent"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--task-id", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--deadline", type=float, default=330)
    p = sub.add_parser("evaluate")
    p.add_argument("--replay-root", required=True, type=Path)
    p.add_argument("--runtime-profile", required=True, type=Path)
    p.add_argument("--runtime-python", required=True, type=Path)
    p.add_argument("--deadline", type=float, default=330)
    p = sub.add_parser("worker")
    p.add_argument("--replay-root", required=True, type=Path)
    p.add_argument("--runtime-profile", required=True, type=Path)
    args = parser.parse_args()
    {"build": build, "evaluate": evaluate, "worker": run_worker}[args.mode](args)


if __name__ == "__main__":
    main()
