from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parents[1] / "scripts" / "benchmark_persistent_preparation.py"
_SPEC = importlib.util.spec_from_file_location("preparation_benchmark", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


@pytest.mark.parametrize("timed_out", [False, True])
def test_k_benchmark_uses_one_frozen_scene_and_reports_stage_timings(tmp_path, timed_out):
    class Client:
        calls = 0

        async def invoke_query_tool(self, tool_id, request, *, caller_id, timeout_ms):
            assert tool_id == "manipulation.prepare"
            assert caller_id == "paos:preparation-benchmark"
            assert timeout_ms == 360_000
            self.calls += 1
            candidates = request["candidates"]
            metric_dir = tmp_path / "preparation-metrics"
            metric_dir.mkdir(exist_ok=True)
            (metric_dir / f"run-{self.calls}.json").write_text(
                json.dumps(
                    {
                        "schema_version": "paos-persistent-preparation-timing/v1",
                        "candidate_count": len(candidates),
                        "scene_revision": request["scene_revision"],
                        "metrics": {
                            "materialization": [
                                {"candidate_ref": item["candidate_ref"], "elapsed_s": 0.01}
                                for item in candidates
                            ],
                            "readiness": [
                                {
                                    "candidate_ref": item["candidate_ref"],
                                    "arm_ids": [arm],
                                    "elapsed_s": 0.02,
                                    "status": "fail",
                                }
                                for item in candidates
                                for arm in ("left", "right")
                            ],
                            "total_s": 0.03,
                        },
                    }
                ),
                encoding="utf-8",
            )
            return {
                "data": {
                    "status": "unavailable" if timed_out else "empty",
                    "scene_revision": "unknown" if timed_out else request["scene_revision"],
                    "motion_authorized": False,
                }
            }

    request = {
        "scene_revision": "scene-1",
        "candidates": [
            {"candidate_ref": f"candidate://green/{index}"}
            for index in range(24)
        ],
    }
    client = Client()
    result = asyncio.run(_MODULE.run_benchmark(client, request, artifact_root=tmp_path))

    assert result["k_values"] == [1, 4, 8, 24]
    assert [len(run["materialization"]) for run in result["runs"]] == [1, 4, 8, 24]
    assert [len(run["readiness"]) for run in result["runs"]] == [2, 8, 16, 48]
    assert all(run["scene_unchanged"] is (None if timed_out else True) for run in result["runs"])
    assert result["query_count"] == 4
    assert result["action_count"] == result["simulator_steps"] == 0
    assert result["motion_authorized"] is False
    assert client.calls == 4
