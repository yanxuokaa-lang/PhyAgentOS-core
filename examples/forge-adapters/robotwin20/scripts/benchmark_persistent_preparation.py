#!/usr/bin/env python3
"""Measure K=1/4/8/24 on one already-running, unchanged persistent scene."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic
from typing import Any, Mapping

from PhyAgentOS.forge.tool_client import ForgeToolClient

DEFAULT_K_VALUES = (1, 4, 8, 24)


def _new_metric(path: Path, previous: set[Path]) -> dict[str, Any]:
    current = set(path.glob("*.json")) if path.is_dir() else set()
    created = current - previous
    if len(created) != 1:
        raise RuntimeError("preparation query did not produce exactly one timing record")
    value = json.loads(created.pop().read_text(encoding="utf-8"))
    if value.get("schema_version") != "paos-persistent-preparation-timing/v1":
        raise RuntimeError("preparation timing record schema is invalid")
    return value


async def run_benchmark(
    client: Any,
    frozen_request: Mapping[str, Any],
    *,
    artifact_root: Path,
    k_values: tuple[int, ...] = DEFAULT_K_VALUES,
) -> dict[str, Any]:
    candidates = frozen_request.get("candidates")
    if not k_values or any(isinstance(k, bool) or not isinstance(k, int) or k <= 0 for k in k_values):
        raise ValueError("k_values must contain positive candidate counts")
    if not isinstance(candidates, list) or len(candidates) < max(k_values):
        raise ValueError(
            f"frozen preparation request requires at least {max(k_values)} candidates"
        )
    metric_dir = artifact_root.resolve() / "preparation-metrics"
    runs: list[dict[str, Any]] = []
    for k in k_values:
        previous = set(metric_dir.glob("*.json")) if metric_dir.is_dir() else set()
        request = deepcopy(dict(frozen_request))
        request["candidates"] = deepcopy(candidates[:k])
        started = monotonic()
        response = await client.invoke_query_tool(
            "manipulation.prepare",
            request,
            caller_id="paos:preparation-benchmark",
            timeout_ms=360_000,
        )
        elapsed = monotonic() - started
        data = response.get("data") if isinstance(response, Mapping) else None
        if not isinstance(data, Mapping):
            raise RuntimeError("preparation benchmark response is invalid")
        timing = _new_metric(metric_dir, previous)
        if timing.get("candidate_count") != k:
            raise RuntimeError("preparation timing record candidate count differs")
        if timing.get("scene_revision") != request.get("scene_revision"):
            raise RuntimeError("preparation timing record scene differs")
        response_scene = data.get("scene_revision")
        scene_unchanged = (
            None if response_scene in (None, "unknown")
            else response_scene == request.get("scene_revision")
        )
        if data.get("motion_authorized") is not False:
            raise RuntimeError("preparation benchmark returned motion authorization")
        runs.append(
            {
                "k": k,
                "status": data.get("status"),
                "elapsed_s": elapsed,
                "materialization": timing["metrics"].get("materialization", []),
                "readiness": timing["metrics"].get("readiness", []),
                "finalization_s": timing["metrics"].get("finalization_s"),
                "provider_total_s": timing["metrics"].get("total_s"),
                "failure": timing["metrics"].get("failure"),
                "scene_unchanged": scene_unchanged,
                "motion_authorized": False,
                "query_count": 1,
                "action_count": 0,
                "simulator_steps": 0,
            }
        )
        if scene_unchanged is False:
            raise RuntimeError("preparation benchmark scene identity changed")
    return {
        "schema_version": "paos-persistent-preparation-benchmark/v1",
        "k_values": list(k_values),
        "runs": runs,
        "motion_authorized": False,
        "query_count": len(runs),
        "action_count": 0,
        "simulator_steps": 0,
    }


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
        suffix=".tmp", delete=False,
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("frozen preparation request must be a JSON object")
    async with ForgeToolClient(args.base_url, timeout_s=360) as client:
        result = await run_benchmark(
            client,
            request,
            artifact_root=args.artifact_root,
        )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    result["provenance"] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "request_path": str(args.request.resolve()),
        "frozen_request": request,
        "artifact_root": str(args.artifact_root.resolve()),
        "base_url": args.base_url,
        "python": platform.python_version(),
        "candidate_order": "input prefix",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:19020")
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; select a new run output path")
    result = asyncio.run(_run(args))
    _write_json_atomic(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
