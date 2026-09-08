"""Task-state-driven outer loop over the PAOS planning adapter.

This module owns no task facts and no execution transport.  It coordinates
checkpointed calls to ``PlanningLoopAdapter`` so a UI can pause, resume, or
inspect a long-running AgentTask without creating a second scheduler.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from PhyAgentOS.agent.planning_loop import PlanningLoopAdapter, PlanningLoopResult
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskStatus


@dataclass(frozen=True)
class LongHorizonTaskResult:
    task_id: str
    status: str
    revision_id: str
    completed_nodes: tuple[str, ...] = ()
    revisions: int = 0
    replans: int = 0
    last_failure: str | None = None


class LongHorizonTaskController:
    """Drive one persisted AgentTask through checkpointed planning turns.

    The controller is deliberately a thin outer seam.  ``AgentTaskCoordinator``
    remains the lifecycle authority and ``PlanningLoopAdapter`` remains the
    only DAG executor.  ``pause()`` takes effect between semantic nodes; an
    in-flight Gateway Action is not cancelled by this method.
    """

    def __init__(
        self,
        coordinator: AgentTaskCoordinator,
        adapter: PlanningLoopAdapter | None = None,
        *,
        scene_revision_provider: Callable[[str], str],
    ) -> None:
        self.coordinator = coordinator
        self.adapter = adapter
        self.scene_revision_provider = scene_revision_provider
        self._locks: dict[str, asyncio.Lock] = {}

    @classmethod
    def for_control(cls, coordinator: AgentTaskCoordinator) -> "LongHorizonTaskController":
        """Create a control-only facade for a UI process.

        Status and checkpoint controls do not need an execution adapter.  Keeping
        this seam on the same controller prevents a CLI/TUI from reaching into
        SQLite or creating a parallel task-control implementation.
        """
        return cls(coordinator, None, scene_revision_provider=lambda _task_id: "")

    def pause(self, task_id: str) -> LongHorizonTaskResult:
        """Request a pause at the next node checkpoint."""
        task = self.coordinator.request_pause(task_id)
        if task.terminal:
            return self._snapshot(task_id)
        return self._snapshot(task_id, status="paused")

    def resume(self, task_id: str) -> LongHorizonTaskResult:
        """Clear a UI pause request; execution still follows task state."""
        self.coordinator.resume_task(task_id)
        return self._snapshot(task_id)

    def status(self, task_id: str) -> LongHorizonTaskResult:
        """Return persisted task/revision status without invoking a Tool."""
        return self._snapshot(task_id)

    async def run(self, task_id: str) -> LongHorizonTaskResult:
        """Run until a terminal, blocked, awaiting-replan, or paused state."""
        if self.adapter is None:
            raise RuntimeError("this controller is control-only; execution adapter is not configured")
        lock = self._locks.setdefault(task_id, asyncio.Lock())
        async with lock:
            task = self.coordinator.get_task(task_id)
            if task.terminal:
                return self._snapshot(task_id)
            if task.status == AgentTaskStatus.AWAITING_REPLAN:
                return self._snapshot(task_id, status="awaiting_replan")
            if task.pause_requested:
                return self._snapshot(task_id, status="paused")

            def checkpoint(current: str) -> bool:
                return not self.coordinator.get_task(current).pause_requested
            result = await self.adapter.run(
                task_id,
                scene_revision=self.scene_revision_provider(task_id),
                checkpoint=checkpoint,
            )
            return self._from_planning_result(result)

    def _from_planning_result(self, result: PlanningLoopResult) -> LongHorizonTaskResult:
        return LongHorizonTaskResult(
            task_id=result.task_id,
            status=result.status,
            revision_id=self.coordinator.get_task(result.task_id).active_revision_id,
            completed_nodes=result.completed_nodes,
            revisions=result.revisions,
            replans=result.replans,
            last_failure=result.last_failure,
        )

    def _snapshot(self, task_id: str, *, status: str | None = None) -> LongHorizonTaskResult:
        task = self.coordinator.get_task(task_id)
        return LongHorizonTaskResult(
            task_id=task_id,
            status=status or ("paused" if task.pause_requested else task.status.value),
            revision_id=task.active_revision_id,
            completed_nodes=tuple(
                item.node_id for item in task.active_revision.node_settlements
                if item.status == "completed"
            ),
            revisions=len(task.revisions),
            replans=max(0, sum(item.counts_toward_replan_budget for item in task.revisions) - 1),
        )


__all__ = ["LongHorizonTaskController", "LongHorizonTaskResult"]
