from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_blocks_ranking_adapter as adapters


def _pose(x: float) -> SimpleNamespace:
    matrix = np.eye(4)
    matrix[0, 3] = x
    return SimpleNamespace(to_transformation_matrix=lambda: matrix)


def _stack_task() -> SimpleNamespace:
    actors = [
        SimpleNamespace(
            get_pose=lambda index=index: _pose(index * 0.1),
            get_functional_point=lambda *_args, index=index: _pose(index * 0.1),
        )
        for index in range(3)
    ]
    return SimpleNamespace(
        block1=actors[0],
        block2=actors[1],
        block3=actors[2],
        check_success=lambda: True,
    )


def test_stack_adapter_exposes_relation_goals_without_static_target_poses(monkeypatch):
    monkeypatch.setattr(adapters, "_half_extents", lambda _actor: [0.02, 0.02, 0.02])
    adapter = adapters.task_adapter("stack_blocks_three")
    task = _stack_task()

    objects = adapter.capture_objects(task, include_targets=False)
    goals = adapter.goal_facts(task, seed=105)
    benchmark = adapter.benchmark_result(task, seed=105, scene_revision="stack-scene-105-1")

    assert adapter.motion_execution_supported is False
    assert [item["entity_ref"] for item in objects] == [
        "entity://stack-block-1", "entity://stack-block-2", "entity://stack-block-3",
    ]
    assert all("target_ref" not in item and "world_T_object_target" not in item for item in objects)
    assert [(item["goal_relation"], item["relation_target_ref"]) for item in goals["goals"]] == [
        ("on", "surface://table"),
        ("on", "entity://stack-block-1"),
        ("on", "entity://stack-block-2"),
    ]
    assert [item["depends_on"] for item in goals["goals"]] == [
        [], ["place_base"], ["place_middle"],
    ]
    assert all(item["produced_evidence"] for item in goals["goals"])
    assert goals["motion_authorized"] is False
    assert "success" not in goals and "score" not in goals
    assert benchmark["success"] is True and benchmark["motion_authorized"] is False


def test_stack_adapter_rejects_static_route_targets_and_unknown_tasks():
    adapter = adapters.task_adapter("stack_blocks_three")
    with pytest.raises(adapters.BlocksRankingRgbTaskAdapterError, match="static route targets"):
        adapter.capture_objects(_stack_task(), include_targets=True)
    with pytest.raises(adapters.BlocksRankingRgbTaskAdapterError, match="does not support"):
        adapters.task_adapter("put_bottles_dustbin")


def test_stack_adapter_cannot_enter_route_preparation_or_action():
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.task_adapter = adapters.task_adapter("stack_blocks_three")

    with pytest.raises(ValueError, match="does not support motion route preparation"):
        engine._query("route_readiness", {})
    with pytest.raises(ValueError, match="does not support motion execution"):
        engine._prepare({})


def test_blocks_ranking_rgb_adapter_remains_motion_capable():
    adapter = adapters.task_adapter("blocks_ranking_rgb")
    assert adapter.motion_execution_supported is True
    assert adapter.entities[0] == ("entity://block-red-1", "block1", "red-slot")
