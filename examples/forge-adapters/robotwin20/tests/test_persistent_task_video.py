from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest
from robotwin_persistent_engine import _TaskVideoArchive
from robotwin_simulation_probe_worker import _artifact_path


class _Cameras:
    def __init__(self) -> None:
        self.value = 0

    def update_picture(self) -> None:
        self.value += 15

    def get_rgb(self):
        return {
            "head_camera": {
                "rgb": np.full((16, 24, 3), self.value, dtype=np.uint8)
            }
        }

    def get_observer_rgb(self):
        return np.full((18, 26, 3), self.value + 5, dtype=np.uint8)


def _task():
    return SimpleNamespace(_update_render=lambda: None, cameras=_Cameras())


def test_engine_records_intermediate_execution_frames(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine, _StopSignal
    from robotwin_simulation_probe_worker import _capture_probe_video

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root, engine.epoch, engine.duration = tmp_path, "test", 30
    engine.stop = _StopSignal(tmp_path / "stop")
    engine.backend = SimpleNamespace(_task=_task(), snapshot=lambda: {"scene_revision": "scene-2"})
    engine.video = _TaskVideoArchive(tmp_path, "test", {"enabled": True, "fps": 10, "stride_steps": 1})
    engine._state = {"simulator_steps": 0, "assignment_ref": "assignment-1"}
    engine._request = {"scene_revision": "scene-1"}
    engine._advance_scene = lambda: "scene-2"
    engine._prepare = lambda _arguments: None
    engine._verify_release = lambda: None

    def phases():
        for phase in ("lift", "retreat"):
            for _ in range(3):
                engine._state["simulator_steps"] += 1
                _capture_probe_video(engine.backend._task, engine._state)
            yield {"phase": phase}
        return {}

    engine._phases = phases()
    for phase in ("acquire", "place"):
        result = engine.execute(
            phase, {"scene_revision": "scene-2", "assignment_ref": "assignment-1"}, Event(),
            owner="paos:task-1", invocation_id=f"invocation://{phase}/1",
        )
        assert result["status"] == "succeeded"
    manifest = json.loads(_artifact_path(tmp_path, result["artifact_refs"][1]).read_text())
    assert manifest["action_count"] == 2
    assert manifest["video_metadata"]["head_camera"]["frame_count"] == 10
    assert manifest["video_metadata"]["observer_camera"]["frame_count"] == 10
    assert "video_recorder" not in engine._state
    from pick_place_workflow.persistent_runtime import _ProjectedDriver

    projected = _ProjectedDriver(
        SimpleNamespace(poll=lambda: result), "place",
        {"frame_id": "world", "scene_revision": "scene-2", "entity_ref": "entity://one"},
    ).poll()
    assert projected["capability_outcome_summary"]["post_release_evidence"] == {
        "availability": "complete", "artifact_refs": result["artifact_refs"],
    }


def test_task_video_accumulates_multiple_actions_into_one_owner_result(tmp_path: Path):
    archive = _TaskVideoArchive(
        tmp_path,
        "epoch-1",
        {"enabled": True, "fps": 10, "stride_steps": 1},
    )
    task = _task()

    archive.start_action(
        task,
        owner="paos:task-1",
        invocation_id="invocation://object-acquire/1",
        phase="acquire",
        simulator_steps=0,
    )
    first_refs = archive.finish_action(
        task, status="succeeded", simulator_steps=10
    )
    for index, phase in enumerate(("place", "acquire", "place"), start=2):
        archive.start_action(
            task, owner="paos:task-1", invocation_id=f"invocation://{phase}/{index}",
            phase=phase, simulator_steps=index * 10,
        )
        final_refs = archive.finish_action(task, status="succeeded", simulator_steps=index * 10 + 10)

    assert len(first_refs) == len(final_refs) == 3
    assert first_refs != final_refs
    manifest = json.loads(_artifact_path(tmp_path, final_refs[0]).read_text())
    assert manifest["owner"] == "paos:task-1"
    assert manifest["action_count"] == 4
    assert [item["phase"] for item in manifest["actions"]] == ["acquire", "place", "acquire", "place"]
    assert manifest["video_metadata"]["head_camera"]["frame_count"] == 8
    assert manifest["video_metadata"]["observer_camera"]["frame_count"] == 8
    assert {manifest["views"][key]["artifact_ref"] for key in manifest["views"]} == set(
        final_refs[1:]
    )
    assert archive.result("paos:task-1") == {
        "availability": "complete",
        "session_id": manifest["session_id"],
        "action_count": 4,
        "actions": manifest["actions"],
        "artifact_refs": list(final_refs),
    }
    assert archive.result("paos:missing") == {
        "availability": "none",
        "action_count": 0,
        "artifact_refs": [],
    }


def test_engine_persists_goal_and_independent_benchmark_results(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    class Adapter:
        def goal_facts(self, _task, *, seed):
            return {
                "schema_version": "paos-task-goals/v1",
                "task_name": "blocks_ranking_rgb",
                "seed": seed,
                "geometry_source": "benchmark_task_definition",
                "goals": [{}],
                "captured_at": "2026-09-20T00:00:00+00:00",
                "motion_authorized": False,
            }

        def benchmark_result(self, _task, *, seed, scene_revision):
            return {
                "schema_version": "paos-robotwin20-benchmark-result/v1",
                "task_name": "blocks_ranking_rgb",
                "seed": seed,
                "scene_revision": scene_revision,
                "success": True,
                "score": 1.0,
                "motion_authorized": False,
            }

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root, engine.epoch = tmp_path, "epoch"
    engine.runtime_profile = {"seed": 3}
    engine.task_adapter = Adapter()
    engine._goal_facts_ref = None
    engine.backend = SimpleNamespace(
        _task=object(), snapshot=lambda: {"scene_revision": "scene-final"}
    )
    engine.video = SimpleNamespace(
        result=lambda owner: {
            "availability": "complete",
            "action_count": 6,
            "artifact_refs": [f"artifact://video/{owner}"],
        }
    )

    first = engine.query("task_goal_facts", {})
    second = engine.query("task_goal_facts", {})
    result = engine.query("benchmark_result", {"task_id": "task-1"})

    assert first["goal_ref"] == second["goal_ref"]
    assert first["motion_authorized"] is False
    assert result["success"] is True
    assert result["task_video"]["action_count"] == 6
    assert _artifact_path(tmp_path, result["artifact_ref"]).is_file()


def test_task_video_starts_a_new_archive_when_owner_changes(tmp_path: Path):
    archive = _TaskVideoArchive(
        tmp_path,
        "epoch-1",
        {"enabled": True, "fps": 10, "stride_steps": 1},
    )
    task = _task()
    for owner in ("paos:task-1", "paos:task-2", "paos:task-1"):
        archive.start_action(
            task,
            owner=owner,
            invocation_id=f"invocation://object-acquire/{owner[-1]}",
            phase="acquire",
            simulator_steps=0,
        )
        refs = archive.finish_action(task, status="succeeded", simulator_steps=1)

    manifest = json.loads(_artifact_path(tmp_path, refs[0]).read_text())
    assert manifest["owner"] == "paos:task-1"
    assert manifest["action_count"] == 2
    assert manifest["video_metadata"]["head_camera"]["frame_count"] == 4


def test_cumulative_publish_failure_keeps_segment_for_next_action(tmp_path, monkeypatch):
    import robotwin_persistent_engine as module

    archive = _TaskVideoArchive(tmp_path, "epoch", {"enabled": True, "fps": 10, "stride_steps": 1})
    task = _task()
    original = module.probe.concatenate_probe_videos
    archive.start_action(task, owner="paos:t", invocation_id="one", phase="acquire", simulator_steps=0)

    def fail(*_args, **_kwargs):
        raise OSError("publish failed")

    monkeypatch.setattr(module.probe, "concatenate_probe_videos", fail)
    with pytest.raises(OSError, match="publish failed"):
        archive.finish_action(task, status="failed", simulator_steps=1)
    monkeypatch.setattr(module.probe, "concatenate_probe_videos", original)
    archive.start_action(task, owner="paos:t", invocation_id="two", phase="place", simulator_steps=1)
    refs = archive.finish_action(task, status="succeeded", simulator_steps=2)
    manifest = json.loads(_artifact_path(tmp_path, refs[0]).read_text())
    assert manifest["action_count"] == 2
    assert manifest["actions"][0]["status"] == "failed"
    assert manifest["video_metadata"]["head_camera"]["frame_count"] == 4
